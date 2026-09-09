import ComparatorDriver

/-- Compare bounded exports and replay with the official kernel without importing
candidate olean files. Nanoda runs separately in another isolated process. -/
def main (args : List String) : IO Unit := do
  let some (configPath : String) := args[0]? | throw <| IO.userError "Missing config"
  let json ← IO.ofExcept <| Lean.Json.parse (← IO.FS.readFile configPath)
  let cfg : Comparator.Config ← IO.ofExcept <| Lean.FromJson.fromJson? json
  if cfg.definition_names.getD #[] != #[] || cfg.enable_nanoda?.getD false ||
      !(cfg.external_kernels?.getD {}).isEmpty then
    throw <| IO.userError "Unsupported comparator configuration"
  if args[1]? == some "targets" then
    let targets ← Comparator.M.run (do
      return (← Comparator.builtinTargets) ++ (← Comparator.getTheoremNames) ++
        (← Comparator.getLegalAxioms) ++ (← Comparator.primitiveTargets)) cfg
    IO.println <| Lean.Json.compress <| Lean.toJson <| targets.map Lean.Name.toString
  else if args[1]? == some "required-targets" then
    let some (solutionPath : String) := args[2]? | throw <| IO.userError "Missing solution export"
    let some (targetsPath : String) := args[3]? | throw <| IO.userError "Missing required targets"
    let targetsJson ← IO.ofExcept <| Lean.Json.parse (← IO.FS.readFile targetsPath)
    let targets : Array String ← IO.ofExcept <| Lean.FromJson.fromJson? targetsJson
    if targets.isEmpty then
      throw <| IO.userError "Empty required target list"
    let solution ← Export.parseStream (← Comparator.stringStream (← IO.FS.readFile solutionPath))
    for target in targets do
      if solution.constMap[target.toName]?.isNone then
        throw <| IO.userError s!"Required candidate declaration missing from export: {target}"
    Comparator.M.run (do
      IO.ofExcept <| Comparator.checkAxioms solution (targets.map String.toName) #[]
        (← Comparator.getLegalAxioms)) cfg
  else
    let some (challengePath : String) := args[1]? | throw <| IO.userError "Missing challenge export"
    let some (solutionPath : String) := args[2]? | throw <| IO.userError "Missing solution export"
    Comparator.M.run (Comparator.verifyMatch (← IO.FS.readFile challengePath)
      (← IO.FS.readFile solutionPath)) cfg
