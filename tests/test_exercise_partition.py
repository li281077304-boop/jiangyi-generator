import sys
from pathlib import Path
from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v1.2-xml-experiment/res/app'))
from exercise_partition import partition_exercises
from semantic_facade import analyze_source


def make_source(tmp_path, lines):
    p = tmp_path / 'source.docx'
    d = Document()
    for line in lines:
        d.add_paragraph(line)
    d.save(p)
    return p, analyze_source(p)


def test_twenty_independent_questions_reserve_one_example_then_split_thirteen_six(tmp_path):
    p,s = make_source(tmp_path, ['%d. Solve independent item %d?'%(i,i) for i in range(1,21)])
    plan, evidence = partition_exercises(p, '1v1', s)
    assert len(plan.slots['knowledge']) == 1
    assert len(plan.slots['immediate']) == 13
    assert len(plan.slots['final']) == 6
    assert plan.omitted_slots == ()
    assert evidence['knowledge_content_mode'] == 'SOURCE_EXAMPLE'
    ids = [span.start for spans in plan.slots.values() for span in spans]
    assert len(set(ids)) == len(ids) == 20


def test_passages_questions_and_inline_answers_stay_whole(tmp_path):
    lines=[]
    for n in range(1,6):
        lines += ['Passage %d'%n, 'A long shared reading material.', '1. A. alpha B. beta',
                  '2. A. gamma B. delta', '参考答案', '1. A', '2. B']
    p,s = make_source(tmp_path, lines)
    plan, evidence = partition_exercises(p, 'class', s)
    routes = {r['source_index']:r['destination_slot'] for r in plan.block_records}
    for start in range(0,len(lines),7):
        assert len({routes[i] for i in range(start,start+7)}) == 1
    assert plan.slots['immediate'] and plan.slots['final']


def test_concentrated_answers_are_not_counted_as_new_questions(tmp_path):
    p,s = make_source(tmp_path, ['%d. Independent problem?'%i for i in range(1,21)]
                      + ['参考答案'] + ['%d. A'%i for i in range(1,21)])
    plan,e = partition_exercises(p, '1v1', s)
    assert len(e['groups']) == 20
    routes = {r['source_index']:r['destination_slot'] for r in plan.block_records}
    assert all(routes[i]=='final' for i in range(20,41))


def test_real_knowledge_is_preserved_without_using_exercises_as_knowledge(tmp_path):
    p,s = make_source(tmp_path, ['基础·知识梳理','A reliable explanation.','1. Method detail',
                      '拔高·分层集训'] + ['%d. Exercise?'%i for i in range(1,11)])
    plan,e = partition_exercises(p,'1v1',s)
    assert {span.start for span in plan.slots['knowledge']} == {'b0','b1','b2'}
    assert plan.slots['immediate'] and plan.slots['final']


def test_explicit_practice_column_ends_knowledge_context_and_keeps_answers(tmp_path):
    lines = ['知识点1 副词的分类', '真实知识讲解。', '优题精练·专题实战通关']
    for i in range(1, 16):
        lines += [f'{i}. Exercise {i}?', f'【答案】answer {i}', f'【解析】explanation {i}']
    p, snapshot = make_source(tmp_path, lines)
    plan, evidence = partition_exercises(p, '1v1', snapshot)
    assert len(evidence['groups']) == 15
    routes = {r['source_index']: r['destination_slot'] for r in plan.block_records}
    assert routes[0] == routes[1] == 'knowledge'
    for start in range(3, len(lines), 3):
        assert len({routes[start], routes[start + 1], routes[start + 2]}) == 1
    assert routes[2] == routes[3] == 'immediate'
    assert plan.slots['knowledge'] and plan.slots['immediate'] and plan.slots['final']


def test_source_example_keeps_entire_passage_and_its_answers(tmp_path):
    lines = []
    for n in range(1, 6):
        lines += [f'Passage {n}', 'A complete shared passage.', '1. First question?',
                  '2. Second question?', '参考答案', '1. A', '2. B']
    path, snapshot = make_source(tmp_path, lines)
    plan, evidence = partition_exercises(path, '1v1', snapshot)
    assert evidence['knowledge_content_mode'] == 'SOURCE_EXAMPLE'
    assert {span.start for span in plan.slots['knowledge']} == {f'b{i}' for i in range(7)}
    ids = [span.start for spans in plan.slots.values() for span in spans]
    assert len(ids) == len(set(ids)) == len(lines)


def test_two_groups_cannot_fake_three_filled_slots(tmp_path):
    from slot_router import SlotRoutingError
    import pytest
    path, snapshot = make_source(tmp_path, ['1. Independent question?', '2. Another question?'])
    with pytest.raises(SlotRoutingError) as failure:
        partition_exercises(path, '1v1', snapshot)
    assert failure.value.reason_code == 'INSUFFICIENT_COMPLETE_GROUPS_FOR_THREE_SLOTS'
