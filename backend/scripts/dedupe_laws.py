"""
상위법령(laws) 테이블 중복 row 탐지/머지 스크립트.

중복 원인: 한글 표기(공백·중점·NFC 등) 차이로 같은 법령이 여러 row로 저장되어,
법제처 API가 돌려준 동일 law_id가 UNIQUE 제약과 충돌함.

그룹화 기준: normalize_name_for_compare(law_name) (NFC + 중점통일 + 공백제거)
keeper(남길 row) 선정:
  1) 법제처 API로 동기화된 적이 있는 row (last_synced_at NOT NULL) 우선
  2) law_id가 0보다 큰 row (placeholder 아님) 우선
  3) id가 가장 작은 row (가장 먼저 등록)

자식 테이블 FK 재지정 (UNIQUE 충돌 시 duplicate 쪽 row 삭제):
  - ordinance_law_mappings        UNIQUE(ordinance_id, law_id)
  - law_changes                   UNIQUE(law_id, sync_batch_id)
  - llm_analysis_results          UNIQUE(ordinance_id, law_id, law_proclaimed_date)
  - revision_detection_results    UNIQUE(ordinance_id, law_id, detection_method)
  - law_revision_reasons          UNIQUE(law_id)   (1:1)
  - amendments.source_law_id      (UNIQUE 없음)

사용:
    # dry-run (기본) — 아무것도 쓰지 않고 계획만 출력
    python -m backend.scripts.dedupe_laws

    # 실제 적용
    python -m backend.scripts.dedupe_laws --apply
"""
import argparse
import asyncio
import logging
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Windows 콘솔 한글 출력용 — ascii 로 폴백되지 않도록 utf-8 강제
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from sqlalchemy import select, update, delete, and_

from backend.core.database import async_session

# SQLAlchemy echo 끄기 — engine 생성 후, child logger 도 끄기
for name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.Engine",
             "sqlalchemy.pool", "sqlalchemy.dialects"):
    lg = logging.getLogger(name)
    lg.setLevel(logging.WARNING)
    lg.propagate = False
from backend.models.law import Law
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.models.law_change import LawChange
from backend.models.llm_analysis_result import LlmAnalysisResult as LLMAnalysisResult
from backend.models.revision_detection_result import RevisionDetectionResult
from backend.models.law_revision_reason import LawRevisionReason
from backend.models.amendment import LawAmendment
from backend.utils.text import normalize_name_for_compare


def pick_keeper(rows):
    """중복 그룹에서 남길 row 선정."""
    def score(law):
        return (
            0 if law.last_synced_at is not None else 1,
            0 if (law.law_id and law.law_id > 0) else 1,
            law.id,
        )
    return sorted(rows, key=score)[0]


async def plan_child_reassign(
    db,
    model,
    keeper_id: int,
    duplicate_id: int,
    conflict_cols: list[str],
):
    """
    duplicate → keeper 재지정 시 UPDATE할 row / DELETE할 row를 분류만 해서 반환.
    실제 쓰지 않음 (dry-run/apply 공통으로 먼저 계획 수립).

    Returns: (update_ids, delete_ids)
    """
    dup_rows = list((await db.execute(
        select(model).where(model.law_id == duplicate_id)
    )).scalars().all())

    if not dup_rows:
        return [], []

    if not conflict_cols:
        # 일반적으로는 단순 UPDATE. 단 UNIQUE(law_id) 같은 경우는 외부에서 처리.
        return [r.id for r in dup_rows], []

    update_ids, delete_ids = [], []
    for dup_row in dup_rows:
        conds = [getattr(model, col) == getattr(dup_row, col) for col in conflict_cols]
        conds.append(model.law_id == keeper_id)
        collision = (
            await db.execute(select(model.id).where(and_(*conds)).limit(1))
        ).scalar_one_or_none()
        if collision:
            delete_ids.append(dup_row.id)
        else:
            update_ids.append(dup_row.id)
    return update_ids, delete_ids


async def apply_child_reassign(db, model, keeper_id: int, update_ids, delete_ids):
    if update_ids:
        await db.execute(
            update(model).where(model.id.in_(update_ids)).values(law_id=keeper_id)
        )
    if delete_ids:
        await db.execute(delete(model).where(model.id.in_(delete_ids)))


async def plan_revision_reason(db, keeper_id: int, duplicate_id: int):
    """
    law_revision_reasons: UNIQUE(law_id), 1:1.
    keeper에 이미 reason이 있으면 duplicate쪽 삭제, 없으면 재지정.
    """
    keeper_has = (await db.execute(
        select(LawRevisionReason.id).where(LawRevisionReason.law_id == keeper_id).limit(1)
    )).scalar_one_or_none()
    dup_ids = [r for r in (await db.execute(
        select(LawRevisionReason.id).where(LawRevisionReason.law_id == duplicate_id)
    )).scalars().all()]
    if not dup_ids:
        return [], []
    if keeper_has:
        return [], dup_ids
    # keeper 없음: 첫 하나만 재지정, 나머지는 삭제
    return dup_ids[:1], dup_ids[1:]


async def dedupe(apply: bool = False):
    async with async_session() as db:
        all_laws = list((await db.execute(select(Law).order_by(Law.id))).scalars().all())
        groups: dict[str, list[Law]] = defaultdict(list)
        for law in all_laws:
            key = normalize_name_for_compare(law.law_name)
            if key:
                groups[key].append(law)

        dup_groups = {k: v for k, v in groups.items() if len(v) > 1}

        print("=" * 80)
        print(f"[전체] laws {len(all_laws)}건, 그룹 {len(groups)}개, 중복 그룹 {len(dup_groups)}개")
        print(f"[모드] {'APPLY (실제 머지)' if apply else 'DRY-RUN (계획만)'}")
        print("=" * 80)

        if not dup_groups:
            print("\n중복 없음.")
            return

        totals = {"groups": 0, "laws_deleted": 0, "reassigned": 0, "deleted_children": 0}

        for key, rows in sorted(dup_groups.items(), key=lambda kv: -len(kv[1])):
            keeper = pick_keeper(rows)
            dups = [r for r in rows if r.id != keeper.id]

            print(f"\n[그룹 '{key}']")
            print(f"  KEEP  id={keeper.id:<5} law_id={keeper.law_id:<10} "
                  f"synced={'Y' if keeper.last_synced_at else 'N'}  '{keeper.law_name}'")
            for d in dups:
                print(f"  DROP  id={d.id:<5} law_id={d.law_id:<10} "
                      f"synced={'Y' if d.last_synced_at else 'N'}  '{d.law_name}'")

            for d in dups:
                summary = []

                for model, cols, label in [
                    (OrdinanceLawMapping, ["ordinance_id"], "ordinance_law_mappings"),
                    (LawChange, ["sync_batch_id"], "law_changes"),
                    (LLMAnalysisResult, ["ordinance_id", "law_proclaimed_date"], "llm_analysis_results"),
                    (RevisionDetectionResult, ["ordinance_id", "detection_method"], "revision_detection_results"),
                ]:
                    upd_ids, del_ids = await plan_child_reassign(db, model, keeper.id, d.id, cols)
                    if apply and (upd_ids or del_ids):
                        await apply_child_reassign(db, model, keeper.id, upd_ids, del_ids)
                    if upd_ids or del_ids:
                        summary.append((label, len(upd_ids), len(del_ids)))
                    totals["reassigned"] += len(upd_ids)
                    totals["deleted_children"] += len(del_ids)

                # law_revision_reasons 특수 처리
                rr_upd, rr_del = await plan_revision_reason(db, keeper.id, d.id)
                if apply and (rr_upd or rr_del):
                    if rr_upd:
                        await db.execute(
                            update(LawRevisionReason)
                            .where(LawRevisionReason.id.in_(rr_upd))
                            .values(law_id=keeper.id)
                        )
                    if rr_del:
                        await db.execute(
                            delete(LawRevisionReason).where(LawRevisionReason.id.in_(rr_del))
                        )
                if rr_upd or rr_del:
                    summary.append(("law_revision_reasons", len(rr_upd), len(rr_del)))
                totals["reassigned"] += len(rr_upd)
                totals["deleted_children"] += len(rr_del)

                # amendments.source_law_id (UNIQUE 없음 → 단순 UPDATE)
                amd_ids = list((await db.execute(
                    select(LawAmendment.id).where(LawAmendment.source_law_id == d.id)
                )).scalars().all())
                if apply and amd_ids:
                    await db.execute(
                        update(LawAmendment)
                        .where(LawAmendment.id.in_(amd_ids))
                        .values(source_law_id=keeper.id)
                    )
                if amd_ids:
                    summary.append(("amendments.source_law_id", len(amd_ids), 0))
                totals["reassigned"] += len(amd_ids)

                for tbl, u, x in summary:
                    print(f"    - {tbl}: reassign={u}, delete={x}")

                # duplicate Law row 삭제
                if apply:
                    await db.execute(delete(Law).where(Law.id == d.id))
                print(f"    - laws.id={d.id} DELETE")
                totals["laws_deleted"] += 1

            totals["groups"] += 1

        if apply:
            await db.commit()
            print("\n[COMMIT] 반영 완료")
        else:
            await db.rollback()
            print("\n[DRY-RUN] 실제 DB 변경 없음. --apply 로 실행 시 반영됩니다.")

        print("\n=== 요약 ===")
        print(f"  처리 그룹:           {totals['groups']}")
        print(f"  삭제 예정 laws row:  {totals['laws_deleted']}")
        print(f"  재지정된 자식 row:   {totals['reassigned']}")
        print(f"  삭제된 자식 row:     {totals['deleted_children']}")


def main():
    parser = argparse.ArgumentParser(description="상위법령 중복 row 머지")
    parser.add_argument("--apply", action="store_true", help="실제 DB에 반영 (기본: dry-run)")
    args = parser.parse_args()
    asyncio.run(dedupe(apply=args.apply))


if __name__ == "__main__":
    main()
