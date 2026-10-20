#!/usr/bin/env python3
"""Read local Codex JSONL accounting without exporting conversation contents."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp needs a UTC offset")
    return parsed.astimezone(timezone.utc)


def records(path, warnings):
    try:
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError()
                    yield row
                except (ValueError, UnicodeError):
                    warnings.add(f"{path.name}:{number}: unreadable JSON record")
    except (OSError, UnicodeError):
        warnings.add(f"{path.name}: could not read log")


def inventory(directory, warnings):
    entries = []
    if not directory.is_dir():
        raise ValueError("sessions directory does not exist")
    for path in sorted(directory.rglob("*.jsonl")):
        # The first metadata belongs to this file; later metadata may be inherited.
        for row in records(path, warnings):
            if row.get("type") == "session_meta":
                meta = row.get("payload", {})
                if isinstance(meta, dict):
                    entries.append((path, meta))
                break
    return entries


def spawn_metadata(meta):
    source = meta.get("source")
    if not isinstance(source, dict):
        return {}
    subagent = source.get("subagent", {})
    spawn = subagent.get("thread_spawn", {}) if isinstance(subagent, dict) else {}
    return spawn if isinstance(spawn, dict) else {}


def automatic(meta):
    source = meta.get("source")
    subagent = source.get("subagent", {}) if isinstance(source, dict) else {}
    return meta.get("thread_source") == "guardian_review" or (
        isinstance(subagent, dict) and subagent.get("other") == "guardian"
    )


def load_session(entries, session_id, warnings):
    roots = [(path, meta) for path, meta in entries if meta.get("id") == session_id
             and not spawn_metadata(meta) and not automatic(meta)]
    if not roots:
        raise ValueError("root session not found; use list to select its full ID")
    selected = {path: meta for path, meta in roots}
    ids = {session_id}
    while True:
        added = False
        for path, meta in entries:
            if path in selected:
                continue
            parent = spawn_metadata(meta).get("parent_thread_id")
            if meta.get("session_id") == session_id or parent in ids:
                selected[path] = meta
                ids.add(meta.get("id"))
                added = True
        if not added:
            break
    agents = {}
    turns = {}
    contexts = {}
    usage = {}
    missing = 0
    legacy_files = set()
    activity = defaultdict(list)
    for path, meta in selected.items():
        identity = meta.get("id")
        spawn = spawn_metadata(meta)
        label = spawn.get("agent_path") or meta.get("agent_path")
        kind = "automatic" if automatic(meta) else "root" if identity == session_id else "subagent"
        agents[identity] = {
            "thread_id": identity, "agent": label or ("/root" if kind == "root" else identity),
            "role": spawn.get("agent_role") or meta.get("agent_role"), "kind": kind,
            "parent_thread_id": spawn.get("parent_thread_id"), "created_at": meta.get("timestamp"),
        }
        has_usage = False
        has_legacy = False
        for row in records(path, warnings):
            payload = row.get("payload", {})
            if not isinstance(payload, dict):
                continue
            kind = row.get("type")
            if kind == "turn_context":
                key = (identity, payload.get("turn_id"))
                contexts[key] = (payload.get("model"), payload.get("effort") or payload.get("reasoning_effort"))
            elif kind == "event_msg":
                event = payload.get("type")
                if event == "token_count":
                    has_legacy = True
                if event == "task_started":
                    try:
                        when = timestamp(row.get("timestamp"))
                        created = timestamp(meta.get("timestamp"))
                        if when >= created:
                            activity[identity].append((payload.get("turn_id"), when))
                    except ValueError:
                        warnings.add("Agent activity has no valid timestamp")
                if identity != session_id or event not in ("task_started", "task_complete", "turn_aborted"):
                    continue
                turn_id = payload.get("turn_id")
                if not turn_id:
                    continue
                turn = turns.setdefault(turn_id, {"turn_id": turn_id, "start": None, "end": None, "status": "incomplete"})
                try:
                    when = timestamp(row.get("timestamp"))
                except ValueError:
                    warnings.add("Turn boundary has no valid timestamp")
                    continue
                if event == "task_started":
                    turn["start"] = min(turn["start"], when) if turn["start"] else when
                else:
                    turn["end"] = max(turn["end"], when) if turn["end"] else when
                    turn["status"] = "complete" if event == "task_complete" else "aborted"
            elif kind == "token_usage_record":
                has_usage = True
                thread = payload.get("thread_id")
                if thread != identity:
                    warnings.add(f"{path.name}: inherited or mismatched thread usage ignored")
                    continue
                response = payload.get("response_id")
                values = payload.get("usage")
                try:
                    when = timestamp(row.get("timestamp"))
                    if not response or not isinstance(values, dict):
                        raise ValueError()
                    if any(type(values.get(key)) is not int or values[key] < 0 for key in FIELDS):
                        raise ValueError()
                    if values["cached_input_tokens"] > values["input_tokens"] or values["reasoning_output_tokens"] > values["output_tokens"]:
                        raise ValueError()
                    writes = values.get("cache_write_input_tokens", 0)
                    if type(writes) is not int or writes < 0:
                        raise ValueError()
                except (ValueError, TypeError):
                    missing += 1
                    warnings.add(f"{path.name}: missing or invalid per-response usage")
                    continue
                item = {"thread_id": thread, "turn_id": payload.get("turn_id"),
                        "when": when, "context": contexts.get((thread, payload.get("turn_id")), (None, None)),
                        "usage": {key: values[key] for key in FIELDS}}
                item["usage"]["cache_write_input_tokens"] = writes
                if response in usage:
                    previous = usage[response]
                    if previous != item:
                        warnings.add("Conflicting response records found; latest timestamp used")
                        if previous["when"] > when:
                            continue
                usage[response] = item
        if has_legacy and not has_usage:
            legacy_files.add(path.name)
    for name in legacy_files:
        warnings.add(f"{name}: cumulative counters only; usage is unknown, not zero")
    return agents, turns, contexts, usage, missing, legacy_files, activity


def iso(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def ordered_turns(turns):
    return sorted((t for t in turns.values() if t["start"]), key=lambda t: (t["start"], t["turn_id"]))


def totals(items):
    result = {key: sum(item["usage"][key] for item in items) for key in (*FIELDS, "cache_write_input_tokens")}
    result["uncached_input_tokens"] = result["input_tokens"] - result["cached_input_tokens"]
    result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    return result


def union_seconds(intervals):
    end = None
    seconds = 0.0
    for start, stop in sorted(intervals):
        if end is None or start > end:
            seconds += (stop - start).total_seconds()
        elif stop > end:
            seconds += (stop - end).total_seconds()
        end = max(end, stop) if end else stop
    return seconds


def report(loaded, session_id, first, last, exclude_agents, include_automatic, pauses, warnings):
    agents, turns, contexts, usage, missing, legacy_files, activity = loaded
    ordered = ordered_turns(turns)
    if not ordered:
        raise ValueError("no root turn boundaries found; cannot safely select task usage")
    ids = [turn["turn_id"] for turn in ordered]
    if first and first not in ids or last and last not in ids:
        raise ValueError("turn not found; use turns to select a full turn ID")
    left = ids.index(first) if first else 0
    right = ids.index(last) if last else len(ids) - 1
    if left > right:
        raise ValueError("from-turn must precede through-turn")
    selected = ordered[left:right + 1]
    selected_ids = {turn["turn_id"] for turn in selected}
    start = selected[0]["start"]
    end = selected[-1]["end"]
    if not end:
        candidates = [item["when"] for item in usage.values() if item["thread_id"] == session_id and item["turn_id"] in selected_ids]
        end = max([start, *candidates])
        warnings.add("Last turn is incomplete; report ends at its latest known root usage")
    if end < start:
        raise ValueError("last turn ends before the selected range starts")
    included = []
    excluded = defaultdict(list)
    groups = defaultdict(list)
    for item in usage.values():
        agent = agents[item["thread_id"]]
        if item["thread_id"] == session_id:
            if item["turn_id"] not in selected_ids:
                continue
        elif not start <= item["when"] <= end:
            continue
        reason = None
        if agent["agent"] in exclude_agents or agent["thread_id"] in exclude_agents:
            reason = "explicit agent exclusion"
        elif agent["kind"] == "automatic" and not include_automatic:
            reason = "automatic approval agent"
        if reason:
            excluded[(agent["thread_id"], reason)].append(item)
            continue
        model, effort = item["context"]
        if not model or not effort:
            warnings.add("Some included responses have unknown model or resolved effort")
        groups[(item["thread_id"], model, effort)].append(item)
        included.append(item)
    unaccounted = []
    root_usage_turns = {item["turn_id"] for item in included if item["thread_id"] == session_id}
    if "/root" not in exclude_agents and session_id not in exclude_agents:
        for turn in selected:
            if turn["turn_id"] not in root_usage_turns:
                unaccounted.append({"thread_id": session_id, "agent": "/root", "turn_id": turn["turn_id"],
                                    "reason": "No valid per-response usage for selected root turn"})
    for thread, agent in agents.items():
        if thread == session_id or agent["agent"] in exclude_agents or thread in exclude_agents:
            continue
        if agent["kind"] == "automatic" and not include_automatic:
            continue
        try:
            created_in_range = start <= timestamp(agent["created_at"]) <= end
        except ValueError:
            created_in_range = False
            warnings.add("Some agents have unknown creation times")
        # Fork snapshots may restamp inherited parent task events at fork time.
        foreign_turns = set(turns) | {item["turn_id"] for item in usage.values() if item["thread_id"] != thread}
        relevant_turns = {turn for turn, when in activity[thread]
                          if start <= when <= end and turn not in foreign_turns}
        known_turns = {item["turn_id"] for item in included if item["thread_id"] == thread}
        missing_turns = relevant_turns - known_turns
        if missing_turns:
            for turn in sorted(missing_turns, key=str):
                unaccounted.append({"thread_id": thread, "agent": agent["agent"], "turn_id": turn,
                                    "reason": "Agent turn starts in range but has no valid per-response usage"})
        elif created_in_range and not known_turns:
            unaccounted.append({"thread_id": thread, "agent": agent["agent"], "turn_id": None,
                                "reason": "Agent has metadata or activity in range but no valid per-response usage"})
    if unaccounted:
        warnings.add("Some selected turns or agents have unknown usage; known totals are partial")
    rows = []
    for (thread, model, effort), items in sorted(groups.items(), key=lambda x: tuple(str(v) for v in x[0])):
        rows.append({**agents[thread], "model": model, "effort": effort,
                     "responses": len(items), **totals(items)})
    if not included:
        warnings.add("No attributable per-response usage found in the selected range")
    intervals = []
    for pause in pauses:
        try:
            a, b = (timestamp(value) for value in pause.split("/", 1))
        except (ValueError, TypeError):
            raise ValueError("pause must be START/END with ISO timestamps") from None
        if b < a:
            raise ValueError("pause end must follow its start")
        if a < end and b > start:
            intervals.append((max(a, start), min(b, end)))
    elapsed = (end - start).total_seconds()
    paused = union_seconds(intervals)
    warnings.add("Subagent usage is selected by response timestamp; concurrent unrelated work or boundary-crossing calls may affect attribution")
    return {
        "schema_version": 1, "session_id": session_id,
        "range": {"from_turn": selected[0]["turn_id"], "through_turn": selected[-1]["turn_id"],
                  "start": iso(start), "end": iso(end)},
        "timing": {"elapsed_seconds": elapsed, "excluded_pause_seconds": paused,
                   "elapsed_without_pauses_seconds": round(elapsed - paused, 6),
                   "pauses": [{"start": iso(a), "end": iso(b)} for a, b in intervals]},
        "agents": rows, "totals": totals(included) if included else None,
        "unaccounted": unaccounted,
        "excluded": [{**agents[thread], "reason": reason, "responses": len(items), **totals(items)}
                     for (thread, reason), items in sorted(excluded.items())],
        "accounting": {"responses": len(included), "invalid_usage_records_in_session": missing,
                       "legacy_only_files_in_session": len(legacy_files),
                       "complete": not missing and not legacy_files and not unaccounted and bool(included)
                       and not any("unreadable" in w or "could not read" in w for w in warnings)},
        "warnings": sorted(warnings),
        "notes": ["Reasoning is included in output; cached input is included in input.",
                  "Explicit pauses adjust elapsed time only, never token counts.",
                  "Recorded model usage is not a bill; no monetary estimate is calculated."],
    }


def cell(value):
    return str(value if value is not None else "unknown").replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def markdown(data):
    lines = [f"Session: {cell(data['session_id'])}", ""]
    if "turns" in data:
        lines += ["| Turn | Start | End | Status | Model | Effort |", "| --- | --- | --- | --- | --- | --- |"]
        for turn in data["turns"]:
            lines.append("| " + " | ".join(cell(turn.get(k)) for k in ("turn_id", "start", "end", "status", "model", "effort")) + " |")
    elif "agents" in data:
        lines += ["| Agent | Model | Effort | Uncached input | Cached input | Output | Reasoning subset | Total |", "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
        for row in data["agents"]:
            lines.append("| " + " | ".join(cell(row.get(k)) for k in ("agent", "model", "effort", "uncached_input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")) + " |")
        lines += ["", "Totals: " + json.dumps(data["totals"], sort_keys=True), "", "Timing: " + json.dumps(data["timing"], sort_keys=True)]
        if data["excluded"]:
            lines += ["", "Excluded:"] + [f"- {cell(row['agent'])}: {row['reason']} ({row['total_tokens']} tokens)" for row in data["excluded"]]
        if data["unaccounted"]:
            lines += ["", "Unknown usage:"] + [f"- {cell(row['agent'])}: {row['reason']}" for row in data["unaccounted"]]
        lines += ["", *data["notes"]]
    lines += ["", "Warnings:", *[f"- {cell(w)}" for w in data["warnings"]]] if data["warnings"] else []
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-dir", type=Path, default=Path.home() / ".codex/sessions")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="discover root sessions without exporting messages")
    listing.add_argument("--cwd", type=Path)
    listing.add_argument("--format", choices=("json", "markdown"), default="markdown")
    for name in ("turns", "report"):
        command = commands.add_parser(name)
        command.add_argument("--session", required=True)
        command.add_argument("--format", choices=("json", "markdown"), default="markdown")
        if name == "report":
            command.add_argument("--from-turn")
            command.add_argument("--through-turn")
            command.add_argument("--exclude-agent", action="append", default=[])
            command.add_argument("--include-automatic", action="store_true")
            command.add_argument("--pause", action="append", default=[], metavar="START/END")
    args = parser.parse_args(argv)
    warnings = set()
    try:
        entries = inventory(args.sessions_dir.expanduser(), warnings)
        if args.command == "list":
            sessions = {}
            for _, meta in entries:
                if spawn_metadata(meta) or automatic(meta):
                    continue
                if args.cwd and Path(meta.get("cwd", "")).resolve() != args.cwd.expanduser().resolve():
                    continue
                identity = meta.get("id")
                if identity:
                    sessions[identity] = {"session_id": identity, "cwd": meta.get("cwd"), "started_at": meta.get("timestamp")}
            data = {"sessions": sorted(sessions.values(), key=lambda x: (x["started_at"] or "", x["session_id"])), "warnings": sorted(warnings)}
            if args.format == "markdown":
                print("| Session | Started | Directory |\n| --- | --- | --- |")
                for session in data["sessions"]:
                    print("| " + " | ".join(cell(session[k]) for k in ("session_id", "started_at", "cwd")) + " |")
                for warning in data["warnings"]:
                    print(f"Warning: {warning}", file=sys.stderr)
                return 0
        else:
            loaded = load_session(entries, args.session, warnings)
            if args.command == "turns":
                rows = []
                for turn in ordered_turns(loaded[1]):
                    model, effort = loaded[2].get((args.session, turn["turn_id"]), (None, None))
                    rows.append({**turn, "start": iso(turn["start"]), "end": iso(turn["end"]), "model": model, "effort": effort})
                data = {"session_id": args.session, "turns": rows, "warnings": sorted(warnings)}
            else:
                data = report(loaded, args.session, args.from_turn, args.through_turn,
                              args.exclude_agent, args.include_automatic, args.pause, warnings)
        print(json.dumps(data, indent=2) if args.format == "json" else markdown(data), end="\n" if args.format == "json" else "")
        return 0
    except (ValueError, OSError) as error:
        # Errors never include raw JSON lines or conversation payloads.
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
