"""Supplemental integer arithmetic, not Lean verification or independent review.

Data transcribed from jyh/dinitz-verify/Submission.lean at
ffba3523f0edd14be3460d039f22a6b98c02fd9e, lines 202-246.
This reviewer-authored script does not import or run upstream code.
It prints a reproducible result and never writes files.
"""
import itertools
import json


def check():
    # Arc label, tail, head, fractional flow, cost.
    arcs = [
        ('st1', 's', 't1', 10, 2), ('st2', 's', 't2', 6, 3),
        ('su', 's', 'u', 24, 0), ('ut3', 'u', 't3', 10, 2),
        ('uv', 'u', 'v', 14, 0), ('vt1', 'v', 't1', 5, 0),
        ('vw', 'v', 'w', 9, 0), ('wt2', 'w', 't2', 4, 0),
        ('wt3', 'w', 't3', 5, 0),
    ]
    demands = {'t1': 15, 't2': 10, 't3': 15}
    ranks = {'s': 0, 'u': 1, 'v': 2, 'w': 3, 't1': 4, 't2': 4, 't3': 4}
    assert len({(tail, head) for _, tail, head, _, _ in arcs}) == len(arcs)
    assert all(ranks[tail] < ranks[head] for _, tail, head, _, _ in arcs)
    assert all(x >= 0 and c >= 0 for _, _, _, x, c in arcs)
    assert all(d > 0 for d in demands.values()) and 's' not in demands
    balances = {}
    for vertex in ranks:
        inflow = sum(x for _, _, head, x, _ in arcs if head == vertex)
        outflow = sum(x for _, tail, _, x, _ in arcs if tail == vertex)
        balances[vertex] = outflow - inflow
        expected = sum(demands.values()) if vertex == 's' else -demands.get(vertex, 0)
        assert balances[vertex] == expected

    def paths(vertex, terminal):
        if vertex == terminal:
            return [()]
        return [(label,) + suffix
                for label, tail, head, _, _ in arcs if tail == vertex
                for suffix in paths(head, terminal)]

    terminals = list(demands)
    choices = [paths('s', terminal) for terminal in terminals]
    dmax = max(demands.values())
    fractional_cost = sum(x * c for _, _, _, x, c in arcs)
    routings = []
    for routing in itertools.product(*choices):
        loads = {label: sum(demands[t] for t, path in zip(terminals, routing)
                            if label in path) for label, *_ in arcs}
        cost = sum(c * loads[label] for label, _, _, _, c in arcs)
        satisfies_load_bound = all(loads[label] <= x + dmax
                                   for label, _, _, x, _ in arcs)
        routings.append({'paths': [list(p) for p in routing], 'cost': cost,
                         'satisfies_load_bound': satisfies_load_bound})
    feasible_costs = [r['cost'] for r in routings if r['satisfies_load_bound']]
    return {
        'meaning': 'Supplemental finite arithmetic only; not a Lean or review approval result.',
        'capacity_choice': 'u = x', 'source_balances_out_minus_in': balances,
        'maximum_demand': dmax, 'fractional_cost': fractional_cost,
        'paths_per_terminal': [len(p) for p in choices],
        'routing_count': len(routings), 'load_feasible_routing_count': len(feasible_costs),
        'minimum_load_feasible_cost': min(feasible_costs),
        'simultaneously_feasible_count': sum(r['satisfies_load_bound'] and r['cost'] <= fractional_cost
                                             for r in routings),
        'routings': routings,
    }


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
