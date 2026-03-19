from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.gram import Flags


class Wordform:
    def __init__(self, form, replaces_base, flags):
        self.form : str = form
        self.replacesBase : bool = replaces_base
        self.flags : Flags = {} if flags is None else flags


    @staticmethod
    def is_replacing_wordform_list(wordforms : list[Wordform]) -> bool:
        if not wordforms or len(wordforms) < 1:
            return False
        return any(filter(lambda wf: wf.replacesBase, wordforms))


    # Returns tuple, first element is matching part of the set, second is non-matching
    @staticmethod
    def filter_wordform_list(source_set : list[Wordform], filter_attributes : Flags) -> tuple[list[Wordform], list[Wordform]]:
        if not source_set or not filter_attributes:
            return source_set, []

        result_pos = []
        result_neg = []
        for wf in source_set:
            wf_fits_filter = True
            for attribute in filter_attributes.keys():
                if not wf.flags:
                    wf_fits_filter = False
                elif attribute in wf.flags and wf.flags[attribute] != filter_attributes[attribute] \
                        and not filter_attributes[attribute] in wf.flags[attribute]:
                    wf_fits_filter = False
            if wf_fits_filter:
                result_pos.append(wf)
            else:
                result_neg.append(wf)

        return result_pos, result_neg


    @staticmethod
    def fetch_wordforms(connection : DbConnection, lexeme_id : int) -> list[Wordform]:
        if not lexeme_id:
            return []
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_wordforms = f"""
    SELECT id, form, data->'Gram'->'Flags' as flags, replaces_base
    FROM {DbConnectionInfo.schema}.wordforms
    WHERE lexeme_id = {lexeme_id}
    """
        cursor.execute(sql_wordforms)
        wordforms = cursor.fetchall()
        if not wordforms:
            return []
        result = []
        for db_row in wordforms:
            result.append(Wordform(db_row['form'], db_row['replaces_base'], db_row['flags']))
        return result
