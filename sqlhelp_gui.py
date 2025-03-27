import sys
import json
import os
from datetime import datetime
import re
from templates.groovy_template import GROOVY_TEMPLATE
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton,
    QComboBox, QTabWidget, QLineEdit, QPlainTextEdit, QMessageBox
)

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
                sql_statements.append(f"            add(SqlMeta.build(\"{check_sql}\", ''' {sql}; '''))")
            else:
                sql_statements.append(f"            add(SqlMeta.build(\"\", ''' {sql}; '''))")

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

class GeneratePage(QWidget):
    def __init__(self):
        super().__init__()
        self.helper = SQLHelper()
        self.config = self.helper.config  # 读取配置
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 数据库选择
        self.db_label = QLabel("选择数据库:")
        self.db_combo = QComboBox()
        self.db_combo.setEditable(True)
        self.db_combo.addItems(self.config.databases)

        # 版本号选择
        self.version_label = QLabel("选择版本号:")
        self.version_combo = QComboBox()
        self.version_combo.setEditable(True)
        self.version_combo.addItems(self.config.versions)

        # 执行区划选择
        self.region_label = QLabel("选择执行区划:")
        self.region_combo = QComboBox()
        self.region_combo.setEditable(True)
        self.region_combo.addItems(self.config.regions)

        # 需求号输入
        self.requirement_label = QLabel("需求号:")
        self.requirement_input = QLineEdit()

        # 脚本说明输入
        self.description_label = QLabel("脚本说明:")
        self.description_input = QLineEdit()

        # SQL 输入框
        self.sql_label = QLabel("SQL语句:")
        self.sql_input = QPlainTextEdit()

        # 提交按钮
        self.submit_button = QPushButton("生成脚本")
        self.submit_button.clicked.connect(self.generate_groovy_file)

        # 添加到布局
        layout.addWidget(self.db_label)
        layout.addWidget(self.db_combo)
        layout.addWidget(self.version_label)
        layout.addWidget(self.version_combo)
        layout.addWidget(self.region_label)
        layout.addWidget(self.region_combo)
        layout.addWidget(self.requirement_label)
        layout.addWidget(self.requirement_input)
        layout.addWidget(self.description_label)
        layout.addWidget(self.description_input)
        layout.addWidget(self.sql_label)
        layout.addWidget(self.sql_input)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def generate_groovy_file(self):
        # 获取用户输入
        user_input = {
            "database": self.db_combo.currentText(),
            "version": self.version_combo.currentText(),
            "region": self.region_combo.currentText(),
            "requirement_id": self.requirement_input.text(),
            "description": self.description_input.text(),
            "sql": self.sql_input.toPlainText()
        }

        if not user_input["requirement_id"] or not user_input["sql"].strip() or not user_input["description"]:
            QMessageBox.warning(self, "输入错误", "需求号、脚本说明、SQL 语句不能为空！")
            return

        try:
            self.helper.create_groovy_file(user_input)
            QMessageBox.information(self, "成功", "SQL 模板文件已生成！")
            # 切换数据库配置
            self.config.move_to_front("databases", user_input["database"])
            self.config.move_to_front("versions", user_input["version"])
            self.config.move_to_front("regions", user_input["region"])
            self.config.save_config()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"文件生成失败: {str(e)}")

class ConfigPage(QWidget):
    def __init__(self):
        super().__init__()
        self.helper = SQLHelper()
        self.config = self.helper.config  # 读取配置
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 数据库配置
        self.db_label = QLabel("数据库列表:")
        self.db_input = QLineEdit(",".join(self.config.databases))
        self.version_label = QLabel("版本号列表:")
        self.version_input = QLineEdit(",".join(self.config.versions))
        self.region_label = QLabel("区划列表:")
        self.region_input = QLineEdit(",".join(self.config.regions))
        self.use_name_label = QLabel("作者名:")
        self.use_name_input = QLineEdit(self.config.responsible_person)
        self.root_path_label = QLabel("根目录:")
        self.root_path_input = QLineEdit(self.config.root_dir)
        self.version_path_label = QLabel("发版目录:")
        self.version_path_input = QLineEdit(self.config.version_dir)

        # 保存按钮
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_config)

        # 添加到布局
        layout.addWidget(self.db_label)
        layout.addWidget(self.db_input)
        layout.addWidget(self.version_label)
        layout.addWidget(self.version_input)
        layout.addWidget(self.region_label)
        layout.addWidget(self.region_input)
        layout.addWidget(self.use_name_label)
        layout.addWidget(self.use_name_input)
        layout.addWidget(self.root_path_label)
        layout.addWidget(self.root_path_input)
        layout.addWidget(self.version_path_label)
        layout.addWidget(self.version_path_input)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def save_config(self):
        try:
            self.config.databases = self.db_input.text().split(",")
            self.config.versions = self.version_input.text().split(",")
            self.config.regions = self.region_input.text().split(",")
            self.config.responsible_person = self.use_name_input.text()
            self.config.root_dir = self.root_path_input.text()
            self.config.version_dir = self.version_path_input.text()
            self.config.save_config()
            QMessageBox.information(self, "成功", "配置已保存！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # 创建QTabWidget
        self.tab1 = QTabWidget()
        # 创建页面
        self.page1 = GeneratePage()
        self.page2 = ConfigPage()
        # 创建 QStackedWidget 并添加页面
        self.tab1.addTab(self.page1, "脚本")
        self.tab1.addTab(self.page2, "配置")
        # 设置默认选中的标签页
        self.tab1.setCurrentIndex(0)
        self.tab1.currentChanged.connect(self.update_config)
        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.tab1)

        self.setLayout(layout)

    def update_config(self, index):
        # 获取最新的配置
        new_config = Config()
        if index == 0:  # 刷新脚本页面
            self.page1.config = new_config
            self.page1.db_combo.clear()
            self.page1.db_combo.addItems(new_config.databases)
            self.page1.version_combo.clear()
            self.page1.version_combo.addItems(new_config.versions)
            self.page1.region_combo.clear()
            self.page1.region_combo.addItems(new_config.regions)

        elif index == 1:  # 刷新配置页面
            self.page2.config = new_config
            self.page2.db_input.setText(",".join(new_config.databases))
            self.page2.version_input.setText(",".join(new_config.versions))
            self.page2.region_input.setText(",".join(new_config.regions))
            self.page2.use_name_input.setText(new_config.responsible_person)
            self.page2.root_path_input.setText(new_config.root_dir)
            self.page2.version_path_input.setText(new_config.version_dir)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle("SQLHelper GUI")
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec_())