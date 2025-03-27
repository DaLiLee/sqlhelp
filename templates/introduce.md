第一步：问题背景及需求分解

提示
“请帮我用 python 开发一个命令行工具 sqlhelp。这个工具的作用是生成特定格式的 Groovy 脚本文件，并根据用户输入的信息填充 SQL 语句。以下是详细需求：”

需求说明
	1.	用户交互：
	•	提示用户依次选择数据库、版本号和执行区划（默认为“通用执行”）。
	•	提示用户输入需求号、说明和 SQL 语句。
	•	提供图形用户界面（GUI）版本，使用下拉框和输入框进行输入。
	2.	文件生成：
	•	根据输入的信息生成文件名格式为：DB_{数据库名}_#{需求号}_{01}_{8位日期}_{说明}.groovy。
	•	文件存放目录格式为：根目录/{版本号}/01.数据库脚本/{执行区划}/。
	•	若目录不存在，则创建。
	3.	SQL 逻辑处理：
	•	将 SQL 语句包装为 add(SqlMeta.build("", '''  ''')) 格式。
	•	根据 SQL 语句类型（如插入数据、新增字段等），生成对应的判断逻辑。
	4.	SQL 版本：MySQL 5.7。
	5.	配置文件 config.json:
	•	包含：根目录、负责人、数据库列表、版本号列表、执行区划列表。

明确目的：
“基于以上需求，分步指导如何使用 python 实现。”

第二步：设置配置文件的加载逻辑

提示
“编写 python 代码，加载配置文件 config.json，结构如下：”

```json
{
  "root_dir": "/Users/zhiaiyoumeng/Downloads/scripts",
  "responsible_person": "负责人",
  "databases": ["db1", "db2"],
  "versions": ["V6.0", "V6.2", "V6.2.ALL"],
  "regions": ["通用执行", "区域A", "区域B"]
}
```

需要实现以下功能：
	1.	加载 JSON 文件到 python 的结构体中。
	2.	如果 JSON 文件不存在，提示错误并退出程序。”

第三步：用户交互

提示
“编写 python 代码，提供命令行交互和图形用户界面（GUI）。功能包括：
	1.	显示数据库列表供选择。
	2.	显示版本号列表供选择。
	3.	显示执行区划列表（默认为“通用执行”）。
	4.	输入需求号、说明和 SQL 语句。”

“最终返回以下结构体数据：”

```python
struct UserInput {
    database: String,
    version: String,
    region: String,
    requirement_id: String,
    description: String,
    sql: String,
}
```

第四步：SQL 语句分类和包装

提示
“分析用户输入的 SQL 语句，判断其类型（如插入数据、新增字段等），并生成相应的判断逻辑。具体规则如下：
	1.	插入数据不带 DELETE：不需要判断 SQL。
	2.	插入数据带 DELETE：添加 DELETE 判断 SQL。
	3.	新增字段：判断字段是否不存在。
	4.	修改字段：判断字段是否存在。
	5.	删除字段：判断字段是否存在。
	6.	新增索引：判断索引是否不存在。
	7.	修改索引：判断索引是否存在。
	8.	新建表：判断表是否不存在。”


第五步：文件名和目录生成

提示
“根据用户输入的数据生成 Groovy 文件名和存储路径：
	1.	文件名格式：DB_{数据库名}_#{需求号}_{01}_{8位日期}_{说明}.groovy。
	2.	文件路径格式：{root_dir}/{版本号}/01.数据库脚本/{执行区划}/。
	3.	如果目录不存在，自动创建目录。
	4.	生成的文件路径和文件名通过日志输出给用户。”
    5.  文件模板参照DB_{数据库名}_#{需求号}_{01}_{8位日期}_{说明}.groovy

第六步：主程序入口

提示
“编写 main.rs 的主程序逻辑，整合以下功能：
	1.	加载配置文件。
	2.	与用户交互，获取输入数据。
	3.	生成 Groovy 文件并写入 SQL 语句。
	4.	输出日志提示成功信息。”

第七步： 输入输出

输入格式

```
请选择数据库：1. db1 2. db2 3. db3
1

请选择版本号：1. V6.0 2. V6.2 3. V6.2.ALL
2

请选择执行区划（直接回车默认为'通用执行'）： 1. 通用执行 2. 区域A 3. 区域B
1

请输入需求号：89679
请输入说明：新建字段
请输入 SQL 语句（输入完成后请输入一个点号(.)并回车）：
alter table gpx_tender.tender_demand_review_record add COLUMN STAGE_PURCHASING_STATUS varchar(2) default 0 null comment '项目分阶段采购标识 1:是,0:否';
alter table gpx_tender.tender_shortlisted add COLUMN ATTACHMENT_NAME varchar(100) default null comment '附件名称';
.

```


“输出结果格式为：”

```groovy
/**
 * 脚本示例
 */
class ScriptExample extends AbstractScriptTpl {
    /**
     * 数据库版本
     * @return
     */
    @Override
    String getSourceVersion() {
        return "{版本}"
    }

    /**
     * 数据库
     * @return
     */
    @Override
    String getDatabase() {
        return "{数据库}"
    }

    /**
     * 版本修改ID
     * @return
     */
    @Override
    String getChangeId() {
        return "{文件名}"
    }

    /**
     * 负责人
     * @return
     */
    @Override
    String getChangeUser() {
        return "{负责人}"
    }

    /**
     * SQL脚本
     * @return
     */
    @Override
    List<SqlMeta> mainSql() {
        return new ArrayList<SqlMeta>() {
            {

                add(SqlMeta.build("SELECT NOT EXISTS(SELECT * FROM `information_schema`.`COLUMNS` WHERE `TABLE_SCHEMA` = 'gpx_tender' AND `TABLE_NAME` = 'tender_demand_review_record' AND `COLUMN_NAME` IN ('STAGE_PURCHASING_STATUS'))", ''' alter table gpx_tender.tender_demand_review_record add COLUMN STAGE_PURCHASING_STATUS varchar(2) default 0 null comment '项目分阶段采购标识 1:是,0:否'; '''))
                add(SqlMeta.build("SELECT NOT EXISTS(SELECT * FROM `information_schema`.`COLUMNS` WHERE `TABLE_SCHEMA` = 'gpx_tender' AND `TABLE_NAME` = 'tender_shortlisted' AND `COLUMN_NAME` IN ('ATTACHMENT_NAME'))", ''' alter table gpx_tender.tender_shortlisted add COLUMN ATTACHMENT_NAME varchar(100) default null comment '附件名称'; '''))
            }
        }
    }
}

```