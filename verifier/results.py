"""Versioned, non-authorizing result summaries shared by PR and revalidation runs."""
import json

from .registry import require, schema_validate


def write_result(path, identifier, proof):
    value = {'schema_version': 1, 'submission_id': identifier,
        'verification_status': proof['verification_status'],
        'machine_status': proof['machine_status'], 'review_status': proof['review_status'],
        'formal_status': 'pending', 'bindings': proof['bindings'],
        'official_targets': proof['targets'], 'candidate_targets': proof['candidate_targets'],
        'completed_stages': proof.get('stages', []), 'failed_stage': proof.get('failed_stage'),
        'input_digest': proof.get('input_digest'), 'image_id': proof.get('image_id'),
        'error': proof.get('error')}
    value['review_approval_kind'] = proof.get('review_approval_kind',
        'independent_review' if proof['review_status'] == 'approved' else 'unapproved')
    value['review_administrator'] = proof.get('review_administrator')
    schema_validate('result', value)
    require((value['review_approval_kind'] == 'unapproved') == (value['review_status'] != 'approved'),
            'Approval kind must match review status')
    require((value['review_approval_kind'] == 'administrator_exception') ==
            (value['review_administrator'] is not None), 'Administrator approval must identify its authority')
    require(value['verification_status'] != 'verified' or
            (value['machine_status'] == 'passed' and value['review_status'] == 'approved'),
            'Verification requires machine success and exact statement approval')
    require(value['verification_status'] != 'review_pending' or
            (value['machine_status'] == 'passed' and value['review_status'] != 'approved'),
            'Pending review is not a machine failure classification')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    from .workflow import progress, write_summary
    write_summary(progress(preparation='ready' if value['review_status'] == 'approved' else 'pending',
                           verification=value['verification_status']), path.with_name('workflow.json'))
    return value
