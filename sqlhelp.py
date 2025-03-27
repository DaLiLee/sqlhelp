import json
import os
from datetime import datetime
import re
from templates.groovy_template import GROOVY_TEMPLATE

# 颜色常量
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
RESET = '\033[0m'

class Config:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.root_dir = config['root_dir']
                self.version_dir = config['version_dir']
                self.responsible_person = config['responsible_person']
                self.databases = config['databases']
                self.versions = config['versions']
                self.regions = config['regions']
        except FileNotFoundError:
            print(f"{RED}错误：找不到配置文件 config.json{RESET}")
            exit(1)
        except json.JSONDecodeError:
            print(f"{RED}错误：config.json 格式不正确{RESET}")
            exit(1)

    def move_to_front(self, list_name, value):
        """将使用过的选项移到列表首位"""
        if hasattr(self, list_name):
            items = getattr(self, list_name)
            if value in items:
                items.remove(value)
            items.insert(0, value)
            setattr(self, list_name, items)
            self.save_config()

    def save_config(self):
        """保存配置到文件"""
        config = {
            'root_dir': self.root_dir,
            'version_dir' : self.version_dir,
            'responsible_person': self.responsible_person,
            'databases': self.databases,
            'versions': self.versions,
            'regions': self.regions
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

class SQLHelper:
    def __init__(self):
        self.config = Config()
        
    def get_user_input(self):
        # 选择数据库
        print("\n请选择数据库（输入数字选择，或直接输入新的数据库名）：")
        for i, db in enumerate(self.config.databases, 1):
            print(f"{GREEN}{i}. {db}{RESET}")
        db_input = input().strip()
        
        try:
            db_choice = int(db_input) - 1
            if 0 <= db_choice < len(self.config.databases):
                database = self.config.databases[db_choice]
                self.config.move_to_front('databases', database)  # 移动到首位
            else:
                raise ValueError()
        except ValueError:
            database = db_input
            if database and database not in self.config.databases:
                print(f"{YELLOW}新数据库 '{database}' 将被添加到配置中{RESET}")
                self.config.databases.insert(0, database)  # 新选项直接添加到首位
                self.config.save_config()

        # 选择版本
        print("\n请选择版本号（输入数字选择，或直接输入新的版本号）：")
        for i, version in enumerate(self.config.versions, 1):
            print(f"{GREEN}{i}. {version}{RESET}")
        version_input = input().strip()
        
        try:
            version_choice = int(version_input) - 1
            if 0 <= version_choice < len(self.config.versions):
                version = self.config.versions[version_choice]
                self.config.move_to_front('versions', version)
            else:
                raise ValueError()
        except ValueError:
            version = version_input
            if version and version not in self.config.versions:
                print(f"{YELLOW}新版本 '{version}' 将被添加到配置中{RESET}")
                self.config.versions.append(version)
                self.config.save_config()

        # 选择执行区划
        print("\n请选择执行区划（直接回车默认为'通用执行'，输入数字选择，或直接输入新的区划）：")
        for i, region in enumerate(self.config.regions, 1):
            print(f"{GREEN}{i}. {region}{RESET}")
        region_input = input().strip()
        
        if not region_input:
            region = self.config.regions[0]
            self.config.move_to_front('regions', region)
        else:
            try:
                region_choice = int(region_input) - 1
                if 0 <= region_choice < len(self.config.regions):
                    region = self.config.regions[region_choice]
                    self.config.move_to_front('regions', region)
                else:
                    raise ValueError()
            except ValueError:
                region = region_input
                if region and region not in self.config.regions:
                    print(f"{YELLOW}新区划 '{region}' 将被添加到配置中{RESET}")
                    self.config.regions.append(region)
                    self.config.save_config()

        # 获取其他输入
        requirement_id = input("\n请输入需求号：")
        description = input("请输入说明：")
        
        print("请输入 SQL 语句（输入完成后请输入一个点号(.)并回车）：")
        sql_statements = []
        current_statement = []
        
        # SQL关键字列表
        sql_keywords = ('ALTER', 'CREATE', 'DROP', 'INSERT', 'UPDATE', 'DELETE')
        
        while True:
            line = input()
            if line.strip() == '.':
                # 处理最后一个语句
                if current_statement:
                    stmt = ' '.join(current_statement)
                    if not stmt.strip().endswith(';'):
                        stmt += ';'
                    sql_statements.append(stmt)
                break
            
            line = line.strip()
            if not line:
                continue
            
            # 检查是否以SQL关键字开头
            is_new_statement = any(line.upper().startswith(keyword) for keyword in sql_keywords)
            
            # 如果是新语句且当前有未完成的语句，先保存当前语句
            if is_new_statement and current_statement:
                stmt = ' '.join(current_statement)
                if not stmt.strip().endswith(';'):
                    stmt += ';'
                sql_statements.append(stmt)
                current_statement = []
            
            # 处理当前行包含分号的情况
            if ';' in line:
                parts = line.split(';')
                # 处理除最后一部分外的所有部分
                for part in parts[:-1]:
                    if part.strip():
                        if current_statement:
                            current_statement.append(part.strip())
                            sql_statements.append(' '.join(current_statement))
                            current_statement = []
                        else:
                            sql_statements.append(part.strip() + ';')
                
                # 处理最后一部分
                last_part = parts[-1].strip()
                if last_part:
                    # 检查最后一部分是否是新语句
                    if any(last_part.upper().startswith(keyword) for keyword in sql_keywords):
                        if current_statement:
                            stmt = ' '.join(current_statement)
                            if not stmt.endswith(';'):
                                stmt += ';'
                            sql_statements.append(stmt)
                        current_statement = [last_part]
                    else:
                        current_statement.append(last_part)
            else:
                # 没有分号的情况
                current_statement.append(line)
        
        return {
            'database': database,
            'version': version,
            'region': region,
            'requirement_id': requirement_id,
            'description': description,
            'sql': '\n'.join(sql_statements)
        }

    def analyze_sql(self, sql):
        sql_metas = []
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for statement in statements:
            if not statement:
                continue
                
            statement_lower = statement.lower()
            
            # 分析SQL类型并生成相应的判断逻辑
            if 'insert into' in statement_lower:
                sql_metas.append(("", statement))
            elif 'delete from' in statement_lower:
                # DELETE 语句不需要检查条件
                sql_metas.append(("", statement))
            elif 'add column' in statement_lower:
                # 新增字段的判断逻辑
                table_schema = re.search(r'`?(\w+)`?\.`?(\w+)`?', statement)
                column_name = re.search(r'add\s+column\s+`?(\w+)`?', statement, re.I)
                if table_schema and column_name:
                    schema, table = table_schema.groups()
                    column = column_name.group(1)
                    check_sql = f"SELECT NOT EXISTS(SELECT * FROM `information_schema`.`COLUMNS` WHERE `TABLE_SCHEMA` = '{schema}' AND `TABLE_NAME` = '{table}' AND `COLUMN_NAME` IN ('{column}'))"
                    sql_metas.append((check_sql, statement))
            
            elif 'modify column' in statement_lower:
                # 修改字段的判断逻辑
                table_schema = re.search(r'`?(\w+)`?\.`?(\w+)`?', statement)
                column_name = re.search(r'modify\s+column\s+`?(\w+)`?', statement, re.I)
                if table_schema and column_name:
                    schema, table = table_schema.groups()
                    column = column_name.group(1)
                    check_sql = f"SELECT EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE table_schema = '{schema}' AND table_name = '{table}' AND column_name = '{column}')"
                    sql_metas.append((check_sql, statement))
            
            elif 'add index' in statement_lower or 'add key' in statement_lower:
                # 新增索引的判断逻辑
                table_schema = re.search(r'`?(\w+)`?\.`?(\w+)`?', statement)
                index_name = re.search(r'add\s+(?:index|key)\s+`?(\w+)`?', statement, re.I)
                if table_schema and index_name:
                    schema, table = table_schema.groups()
                    index = index_name.group(1)
                    check_sql = f"SELECT NOT EXISTS (SELECT * FROM information_schema.statistics WHERE table_schema='{schema}' AND table_name = '{table}' AND index_name = '{index}')"
                    sql_metas.append((check_sql, statement))
            else:
                # 对于其他类型的SQL，不添加判断逻辑
                sql_metas.append(("", statement))
                
        return sql_metas

    def generate_file_name(self, user_input):
        date_str = datetime.now().strftime('%Y%m%d')
        # 数据库名使用大写
        db_name = user_input['database'].upper()
        requirement_id = user_input['requirement_id']
        
        # 如果 requirement_id 包含 @，则不加 #
        requirement_part = requirement_id if '@' in requirement_id else f"#{requirement_id}"
        
        return f"DB_{db_name}_{requirement_part}_01_{date_str}_{user_input['description']}"

    def generate_groovy_content(self, user_input, sql_metas):
        sql_statements = []
        for check_sql, sql in sql_metas:
            if check_sql:
                sql_statements.append(f"                add(SqlMeta.build(\"{check_sql}\", ''' {sql}; '''))")
            else:
                sql_statements.append(f"                add(SqlMeta.build(\"\", ''' {sql}; '''))")

        return GROOVY_TEMPLATE.format(
            version=user_input['version'],
            database=user_input['database'].lower(),  # 数据库名使用小写
            change_id=self.generate_file_name(user_input),  # 不包含.groovy后缀
            responsible_person=self.config.responsible_person,
            sql_statements='\n'.join(sql_statements)
        )

    def create_groovy_file(self, user_input):
        # 子文件夹
        note = user_input.get('database', '')
        # 确保 note 是字符串，并进行安全分割
        note = note.rsplit('_', 1)[-1] if '_' in note else note
        note = note.rsplit('-', 1)[-1] if '-' in note else note
        dir_path = os.path.join(
            self.config.root_dir,
            user_input['version'],
            '01.数据库脚本',
            user_input['region'],
            note
        )
        # 父文件夹
        prent = self.get_parent_folder(user_input['version'])

        version_dir = os.path.join(
            self.config.version_dir,
            prent,
            user_input['version'],
            '01.数据库脚本',
            user_input['region'],
            note
        )
        os.makedirs(dir_path, exist_ok=True)

        # 生成文件名和内容
        file_name = self.generate_file_name(user_input) + '.groovy'  # 这里添加.groovy后缀
        file_path = os.path.join(dir_path, file_name)
        
        # 分析SQL并生成内容
        sql_metas = self.analyze_sql(user_input['sql'])
        content = self.generate_groovy_content(user_input, sql_metas)

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"\n文件已生成：{file_path}")
        print(f"\n文件路径：{dir_path}")
        print(f"\n版本路径：{version_dir}")
        
    def get_parent_folder(self, version):
        match = re.match(r'^(V\d+)\.(\d+)', version)  # 提取主版本号 (Vx) 和次版本号 (y)
        if match:
            major_version, minor_version = match.groups()  # major_version = "V7", minor_version = "1"
            return f"{major_version}.0/{major_version}.{minor_version}"  # 生成 "V7.0/V7.1" 格式
        return "V6.0"  # 默认情况


def main():
    helper = SQLHelper()
    user_input = helper.get_user_input()
    helper.create_groovy_file(user_input)

if __name__ == "__main__":
    main()
