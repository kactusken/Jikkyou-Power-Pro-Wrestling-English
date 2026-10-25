-- Max Voltage: load save slot 1 from the title screen and stop at the career hub, before the
-- month starts (tools/mesen.py: load a title state, write sram 0 FILE.srm, then
-- autoplay 3000 tools/mvload.lua [slot=1|2|3]). Title: Start, Down x3 (Max Voltage), Start;
-- slot list: Down to the slot, B; resume box: B (Start). Stops as soon as the slot is loaded
-- ($48 = 6 with a career date and promotion in $1FE3/$1FE7 after the last press), before the
-- month's intro and start-of-month event, so the next autoplay sees (and records) them.
local plan, pulse, t = nil, 0, 0
return function(f, api)
  local m, p = api.rb(0x1FE3), api.rb(0x1FE7)
  if plan and #plan == 0 and api.rb(0x48) == 6 and m >= 1 and m <= 12 and p >= 2 and p <= 5 then
    return "stop"
  end
  if not plan then
    local D, S, B = {down = true}, {start = true}, {b = true}
    plan = {"w", S, "w", "w", D, D, D, S, "w", "w", "w"}
    for _ = 2, tonumber(api.args.slot or "1") do plan[#plan + 1] = D end
    plan[#plan + 1] = B; plan[#plan + 1] = "w"; plan[#plan + 1] = B
  end
  t = t + 1
  local step = plan[1]
  if not step then if t % 60 < 6 then return {b = true} end return nil end  -- keep confirming
  if step == "w" then if t >= 120 then t = 0; table.remove(plan, 1) end return nil end
  if t <= 6 then return step end
  if t >= 30 then t = 0; table.remove(plan, 1) end
  return nil
end
