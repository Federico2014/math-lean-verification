"""Four user-facing stages; these summaries never authorize proof or acceptance."""
import json
import os
from pathlib import Path

STEPS = (
    'Submit candidate',
    'Clear prerequisites',
    'Verify proof',
    'Merge, publish and accept',
)
WAITING = {'needs_information', 'waiting_problem', 'waiting_review',
           'waiting_environment', 'needs_adaptation', 'review_pending', 'unsupported'}


def progress(*, preparation='pending', verification='not_run', registered=False,
             acceptance=None):
    ready = preparation == 'ready'
    verified = ready and verification == 'verified'
    current = 2 if not ready else 3 if not verified else 4
    steps = [
        {'step': 1, 'name': STEPS[0], 'status': 'complete'},
        {'step': 2, 'name': STEPS[1], 'status': 'complete' if ready else preparation if preparation in WAITING else 'waiting'},
        {'step': 3, 'name': STEPS[2], 'status': 'complete' if verified else verification},
        {'step': 4, 'name': STEPS[3], 'status': 'registered' if registered else 'pending'},
    ]
    # Historical acceptance and current proof status remain separate facts.
    return {'schema_version': 1, 'current_step': current, 'steps': steps,
            'registered': registered,
            'formal_status': 'accepted_historical' if acceptance else 'pending',
            'next_action': (
                'Resolve the prerequisite blockers; keep the candidate PR open.' if not ready else
                'Inspect or run trusted verification for the current inputs.' if not verified else
                'Merge the candidate PR through normal branch protection.' if not registered else
                'Registration published; acceptance remains bound to its recorded revisions.' if acceptance else
                'Registration published; an explicit acceptance decision and durable archive are still required.')}


def from_plan(plan, *, registered=False):
    status = plan.get('status')
    blocked = plan.get('blocked') or {}
    proofs = list((plan.get('submissions') or {}).values())
    preparation = 'ready' if status in ('ready', 'passed') else 'pending'
    verification = 'verified' if status == 'passed' else 'not_run'
    if status == 'failed' and any(p.get('machine_status') in ('passed', 'failed') or p.get('stages') for p in proofs):
        preparation = 'ready'
        verification = next((p.get('verification_status', 'failed') for p in proofs
                             if p.get('verification_status') != 'verified'), 'failed')
    if any(p.get('review_status') in ('pending', 'rejected', 'invalidated') for p in proofs):
        preparation = 'waiting_review'
    if blocked:
        codes = [p.get('intake_status', p.get('status')) for p in blocked.values()]
        preparation = next((code for code in codes if code in WAITING), 'pending')
    value = progress(preparation=preparation, verification=verification, registered=registered)
    value['blocked_candidates'] = sorted(blocked)
    return value


def write_summary(value, path=None, *, emit=True):
    if path:
        with Path(path).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary and emit:
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write('## Candidate workflow\n\n')
            for step in value['steps']:
                stream.write(f"- {step['step']}. {step['name']}: {step['status']}\n")
            stream.write('\n' + value['next_action'] + '\n')
