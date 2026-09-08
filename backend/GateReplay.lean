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
  else
    let some (challengePath : String) := args[1]? | throw <| IO.userError "Missing challenge export"
    let some (solutionPath : String) := args[2]? | throw <| IO.userError "Missing solution export"
    Comparator.M.run (Comparator.verifyMatch (← IO.FS.readFile challengePath)
      (← IO.FS.readFile solutionPath)) cfg
