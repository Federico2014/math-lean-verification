"""Real positive and adversarial proof tests; requires an immutable backend image."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verifier.lean_backend import verify
from verifier.environments import load_environments
from verifier.registry import ROOT
from verifier.source_adaptation import adapt

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
        # Exporters may silently omit unknown declarations. A valid official
        # bridge must not hide a missing or axiom-dependent registered target.
        for name, extra, declarations in [
            ('missing_upstream_target', '', ['upstream', 'missing_upstream']),
            ('unproved_upstream_target', '\ntheorem unproved : False := by sorry\n', ['upstream', 'unproved']),
        ]:
            (root/'solution/Proofs/Main.lean').write_text(prefix +
                'theorem upstream (n : Nat) : n + 0 = n := by rfl\n' + extra)
            result = verify(args.image, root/'challenge', root/'solution', 'Bridge', ['target'], args.output/name,
                            environment=environment, solution_declarations=declarations)
            reason = ('Required candidate declaration missing from export: missing_upstream' if not extra else 'sorryAx')
            okay = (result['machine_status'] == 'failed' and 'solution_clean_build_export' in result['stages']
                    and 'candidate_target_coverage' not in result['stages'] and reason in result.get('error', ''))
            results.append({'case': name, 'test_passed': okay, 'error': result.get('error')})
            print(json.dumps(results[-1]), flush=True)
    # The common source adapter must support an upstream Challenge module without
    # allowing the candidate to replace the official Challenge input.
    for borrows_placeholder in (False, True):
        name = 'adapted_challenge_sorry' if borrows_placeholder else 'adapted_challenge'
        with tempfile.TemporaryDirectory(prefix='lean-adapt-') as folder:
            root = Path(folder)
            (root/'challenge').mkdir(); (root/'solution').mkdir()
            definition = 'def claim (n : Nat) : Prop := n + 0 = n\n'
            (root/'challenge/Challenge.lean').write_text(prefix + definition +
                'theorem official (n : Nat) : claim n := by sorry\n')
            original_challenge = (prefix + definition +
                'theorem placeholder (n : Nat) : claim n := by sorry\n').encode()
            original_solution = ('import Challenge\ntheorem upstream (n : Nat) : claim n := ' +
                ('placeholder n\n' if borrows_placeholder else 'by rfl\n')).encode()
            for path, data, destination, replacements in [
                ('Challenge.lean', original_challenge, 'CandidateChallenge.lean', []),
                ('Submission.lean', original_solution, 'Submission.lean',
                 [{'old':'import Challenge\n','new':'import CandidateChallenge\n','count':1}]),
            ]:
                transform = {'destination':destination,'sha256':hashlib.sha256(data).hexdigest(),'replacements':replacements}
                target, changed = adapt(path, data, transform, max_bytes=1024*1024)
                (root/'solution'/target).write_bytes(changed)
            (root/'solution/Bridge.lean').write_text('import Submission\ntheorem official (n : Nat) : claim n := upstream n\n')
            result = verify(args.image, root/'challenge', root/'solution', 'Bridge', ['official'],
                            args.output/name, environment=environment, solution_declarations=['upstream'])
            okay = (result['machine_status'] == ('failed' if borrows_placeholder else 'passed') and
                    'solution_clean_build_export' in result['stages'])
            if borrows_placeholder:
                okay = okay and 'sorryAx' in result.get('error', '')
            results.append({'case':name,'test_passed':okay,'error':result.get('error')})
            print(json.dumps(results[-1]), flush=True)
    # Check every declared cache entry is actually importable offline. These are
    # availability probes, not proof compatibility evidence for arbitrary users
    # of those modules; each candidate still undergoes the complete check chain.
    if environment and environment['dependency_mode'] == 'mathlib-cache':
        for module in environment['cache_modules'] or ['Mathlib']:
            name = 'cache-import-' + module
            with tempfile.TemporaryDirectory(prefix='lean-import-') as folder:
                root = Path(folder)
                (root/'challenge').mkdir(); (root/'solution').mkdir()
                (root/'challenge/Challenge.lean').write_text('import ' + module + '\ntheorem target : True := by sorry\n')
                (root/'solution/Solution.lean').write_text('import ' + module + '\ntheorem target : True := by trivial\n')
                result = verify(args.image, root/'challenge', root/'solution', 'Solution', ['target'],
                                args.output/name, environment=environment)
                results.append({'case':name,'test_passed':result['machine_status'] == 'passed','error':result.get('error')})
                print(json.dumps(results[-1]), flush=True)
    (args.output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    return 0 if all(r['test_passed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
