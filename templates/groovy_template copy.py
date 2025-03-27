GROOVY_TEMPLATE = '''/**
 * 脚本示例
 */
class ScriptExample extends AbstractScriptTpl {{
    /**
     * 数据库版本
     * @return
     */
    @Override
    String getSourceVersion() {{
        return "{version}"
    }}

    /**
     * 数据库
     * @return
     */
    @Override
    String getDatabase() {{
        return "{database}"
    }}

    /**
     * 版本修改ID
     * @return
     */
    @Override
    String getChangeId() {{
        return "{change_id}"
    }}

    /**
     * 负责人
     * @return
     */
    @Override
    String getChangeUser() {{
        return "{responsible_person}"
    }}

    /**
     * SQL脚本
     * @return
     */
    @Override
    List<SqlMeta> mainSql() {{
        return new ArrayList<SqlMeta>() {{{{
{sql_statements}
        }}}}
    }}
}}
''' 