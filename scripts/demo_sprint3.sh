#!/usr/bin/env bash
# Sprint 3 end-to-end verification over the scenario API (all Fake-backed).
# Requires the API running:  poetry run uvicorn api.main:app --port 8000
# Usage: BASE_URL=http://localhost:8000 bash scripts/demo_sprint3.sh
set -euo pipefail
BASE="${BASE_URL:-http://localhost:8000}"
CT='Content-Type: application/json'
get() { python3 -c "import sys,json;print(json.load(sys.stdin)$1)"; }
pp() { python3 -m json.tool; }

echo "== 1. create scenario =="
SID=$(curl -s -X POST "$BASE/scenarios" -H "$CT" \
  -d '{"domain":"card_game","name":"Cyberpunk","brief":"cyberpunk deck cheap aggressive units","n_entities":5}' \
  | get "['id']")
echo "scenario id: $SID"

echo "== 2. design (Fake Designer -> 5 units) =="
curl -s -X POST "$BASE/scenarios/$SID/iterate" -H "$CT" -d '{"phase":"design"}' | pp

echo "== 3. objectives (maximize variety + minimize winrate spread) =="
curl -s -X POST "$BASE/scenarios/$SID/objectives" -H "$CT" \
  -d '{"objectives":[{"metric_name":"variety","direction":"maximize","weight":1.0},
                     {"metric_name":"winrate_std","direction":"minimize","weight":1.0}]}' | pp

echo "== 4. simulate =="
curl -s -X POST "$BASE/scenarios/$SID/iterate" -H "$CT" -d '{"phase":"simulate"}' | pp

echo "== 5. judge =="
curl -s -X POST "$BASE/scenarios/$SID/iterate" -H "$CT" -d '{"phase":"judge"}' | pp

echo "== 6. user edits an entity manually =="
NAME=$(curl -s "$BASE/scenarios/$SID" | get "[sorted(json.load(sys.stdin)['entities'])[0]]" 2>/dev/null || true)
NAME=$(curl -s "$BASE/scenarios/$SID" | python3 -c "import sys,json;print(sorted(json.load(sys.stdin)['entities'])[0])")
echo "editing: $NAME"
curl -s -X PATCH "$BASE/scenarios/$SID/entities/$NAME" -H "$CT" \
  -d "{\"entity\":{\"name\":\"$NAME\",\"cost\":1,\"hp\":20,\"damage\":10,\"ability_kind\":\"shield\",\"ability_value\":5,\"description\":\"user buffed\"}}" | pp

echo "== 7. iterate (FakeIterator proposes; must respect user authorship) =="
curl -s -X POST "$BASE/scenarios/$SID/iterate" -H "$CT" -d '{"phase":"iterate"}' | pp

echo "== 8. branch =="
HEAD=$(curl -s "$BASE/scenarios/$SID" | get "['head_seq']")
curl -s -X POST "$BASE/scenarios/$SID/branches" -H "$CT" -d "{\"parent_seq\":$HEAD,\"name\":\"alt\"}" | pp

echo "== 9. diff main vs alt =="
curl -s "$BASE/scenarios/$SID/branches/main/diff/alt" | pp

echo "$SID"
