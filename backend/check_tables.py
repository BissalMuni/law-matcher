#!/usr/bin/env python
"""
데이터베이스 테이블 구조 확인 스크립트
"""
from sqlalchemy import create_engine, inspect, MetaData
from core.config import settings

def check_table_structure():
    """테이블 구조 확인"""
    # asyncpg URL을 psycopg2 URL로 변경
    db_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    engine = create_engine(db_url)
    inspector = inspect(engine)

    # Article 관련 테이블만 선택
    article_tables = [
        'articles',
        'article_changes',
        'ordinance_article_mappings'
    ]

    for table_name in article_tables:
        if table_name not in inspector.get_table_names():
            print(f"⚠️  테이블 '{table_name}'이 존재하지 않습니다.\n")
            continue

        print(f"\n{'='*80}")
        print(f"📋 테이블: {table_name}")
        print(f"{'='*80}\n")

        # 컬럼 정보
        columns = inspector.get_columns(table_name)
        print("📊 컬럼 구조:")
        print(f"{'컬럼명':<30} {'타입':<25} {'Nullable':<10} {'기본값'}")
        print("-" * 80)

        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            nullable = 'NULL' if col['nullable'] else 'NOT NULL'
            default = col.get('default', '-')
            if default is None:
                default = '-'

            print(f"{col_name:<30} {col_type:<25} {nullable:<10} {default}")

        # 인덱스 정보
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print("\n🔍 인덱스:")
            for idx in indexes:
                idx_name = idx['name']
                idx_cols = ', '.join(idx['column_names'])
                unique = '(UNIQUE)' if idx.get('unique') else ''
                print(f"  - {idx_name}: {idx_cols} {unique}")

        # 외래키 정보
        foreign_keys = inspector.get_foreign_keys(table_name)
        if foreign_keys:
            print("\n🔗 외래키:")
            for fk in foreign_keys:
                fk_name = fk.get('name', 'unnamed')
                local_cols = ', '.join(fk['constrained_columns'])
                ref_table = fk['referred_table']
                ref_cols = ', '.join(fk['referred_columns'])
                on_delete = fk.get('options', {}).get('ondelete', 'NO ACTION')
                print(f"  - {fk_name}: {local_cols} -> {ref_table}({ref_cols}) [ON DELETE {on_delete}]")

        # 제약조건 (UNIQUE)
        unique_constraints = inspector.get_unique_constraints(table_name)
        if unique_constraints:
            print("\n🔐 UNIQUE 제약조건:")
            for uc in unique_constraints:
                uc_name = uc.get('name', 'unnamed')
                uc_cols = ', '.join(uc['column_names'])
                print(f"  - {uc_name}: {uc_cols}")

        print()

    print(f"\n{'='*80}")
    print("✅ 테이블 구조 확인 완료!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    check_table_structure()
