"""Real positive and adversarial proof tests; requires an immutable backend image."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verifier.lean_backend import verify
from verifier.environments import load_environments
from verifier.registry import ROOT

BASE = 'theorem target (n : Nat) : n + 0 = n := '
CASES = [
    ('valid', BASE + 'by sorry\n', BASE + 'by rfl\n', ['target'], True),
    ('irrelevant_sorry', BASE + 'by sorry\n',
     'theorem unused : False := by sorry\n' + BASE + 'by rfl\n', ['target'], True),
    ('sorry', BASE + 'by sorry\n', BASE + 'by sorry\n', ['target'], False),
    ('indirect_sorry', BASE + 'by sorry\n',
     'theorem hole (n : Nat) : n + 0 = n := by sorry\n' + BASE + 'hole n\n', ['target'], False),
    ('extra_axiom', BASE + 'by sorry\n',
     'axiom magic : ∀ n : Nat, n + 0 = n\n' + BASE + 'magic n\n', ['target'], False),
    ('wrong_statement', BASE + 'by sorry\n', 'theorem target (n : Nat) : True := by trivial\n', ['target'], False),
    ('extra_premise', BASE + 'by sorry\n',
     'theorem target (n : Nat) (h : False) : n + 0 = n := by cases h\n', ['target'], False),
    ('changed_definition', 'def value : Nat := 7\ntheorem target : value = value := by sorry\n',
     'def value : Nat := 8\ntheorem target : value = value := by rfl\n', ['target'], False),
    ('missing_target', BASE + 'by sorry\ntheorem other : True := by sorry\n', BASE + 'by rfl\n', ['target','other'], False),
    ('forged_stdout', BASE + 'by sorry\n',
     '#eval IO.println "Your solution is okay!"\n' + BASE + 'by sorry\n', ['target'], False),
    ('unchecked_kernel_declaration', 'theorem target : False := by sorry\n',
     'import Lean\nset_option debug.skipKernelTC true\nrun_elab Lean.addDecl <| .thmDecl { name := `target, levelParams := [], type := Lean.mkConst ``False, value := Lean.mkConst ``True.intro }\n', ['target'], False),
    ('protected_write', BASE + 'by sorry\n',
     '#eval IO.FS.writeFile "/input/source/Challenge.lean" "theorem target : True := by trivial"\n' + BASE + 'by rfl\n', ['target'], False),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--environment')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    environment = load_environments(ROOT)[args.environment] if args.environment else None
    prefix = 'import Mathlib.Data.Nat.Basic\n' if environment and environment['dependency_mode'] == 'mathlib-cache' else ''
    results = []
    cases = list(CASES)
    if prefix:
        cases.append(('mathlib_lemma', 'theorem target : Function.Injective Nat.succ := by sorry\n',
                      'theorem target : Function.Injective Nat.succ := Nat.succ_injective\n', ['target'], True))
    for name, challenge, solution, targets, expected in cases:
        with tempfile.TemporaryDirectory(prefix='lean-fixture-') as folder:
            root = Path(folder)
            for directory, filename, text in [('challenge','Challenge.lean',challenge),('solution','Solution.lean',solution)]:
                (root/directory).mkdir()
                (root/directory/filename).write_text(prefix + text)
            result = verify(args.image, root/'challenge', root/'solution', 'Solution', targets, args.output/name, environment=environment)
        passed = result['machine_status'] == 'passed'
        okay = passed == expected and 'challenge_clean_build_export' in result['stages']
        if not expected and name not in ('missing_target', 'protected_write'):
            okay = okay and 'solution_clean_build_export' in result['stages']
        results.append({'case': name, 'expected_accept': expected, 'actual_accept': passed,
                        'test_passed': okay, 'stages': result['stages'], 'error': result.get('error')})
        print(json.dumps(results[-1]), flush=True)
    # Multi-file project and an explicitly checked bridge to a differently named theorem.
    with tempfile.TemporaryDirectory(prefix='lean-bridge-') as folder:
        root = Path(folder)
        (root/'challenge').mkdir(); (root/'solution/Proofs').mkdir(parents=True)
        (root/'challenge/Challenge.lean').write_text(prefix + BASE + 'by sorry\n')
        (root/'solution/Proofs/Main.lean').write_text(prefix + 'theorem upstream (n : Nat) : n + 0 = n := by rfl\n')
        (root/'solution/Bridge.lean').write_text('import Proofs.Main\n' + BASE + 'upstream n\n')
        result = verify(args.image, root/'challenge', root/'solution', 'Bridge', ['target'], args.output/'bridge',
                        environment=environment, solution_declarations=['upstream'])
        okay = result['machine_status'] == 'passed' and 'independent_nanoda_replay' in result['stages']
        results.append({'case': 'multi_file_bridge', 'test_passed': okay, 'error': result.get('error')})
        print(json.dumps(results[-1]), flush=True)
    (args.output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    return 0 if all(r['test_passed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
