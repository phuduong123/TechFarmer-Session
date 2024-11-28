from datetime import datetime
from nicegui import events, ui

# Add Tailwind CSS to the head of the HTML
ui.add_head_html('<link rel="stylesheet" href="/static/css/output.css">')

# Data storage for sessions
session_data = []

@ui.page('/')
def main():
    with ui.row().classes('items-center w-full p-4 bg-blue-400'):
        ui.image('./static/images/icons/welcomeIcon.png') \
            .classes('h-10 w-10 ml-4')
        ui.label('FarmTech // Working with session') \
            .classes('text-4xl font-bold text-white')

    # Input section
    with ui.card().classes('p-8 bg-gray-100 rounded-lg shadow-lg w-full'):
        ui.label('Nhập số điện thoại:').classes('text-lg font-semibold text-gray-700 mb-2')
        phone_input = ui.input('Enter phone number').classes('w-full px-4 py-2 border rounded-lg mb-4')

        ui.label('Chọn session file:').classes('text-lg font-semibold text-gray-700 mb-2')
        session_file_input = ui.upload(label='Select session file').classes('mb-4 w-full')

        # Placeholder for the file path
        file_path_label = ui.label('').classes('text-sm text-gray-500 mb-4')

        # Update file path dynamically
        def handle_file_upload(files):
            if files:
                file_path = files[0]['path']  # Assuming NiceGUI's upload provides 'path'
                file_path_label.text = f"Đường dẫn file: {file_path}"
                ui.notify(f"Tải lên thành công: {file_path}")
                session_data.append({'phone': phone_input.value, 'file_path': file_path, 'created_at': datetime.now()})

        session_file_input.on('upload', handle_file_upload)

        # Submit button
        def submit():
            if not phone_input.value:
                ui.notify('Vui lòng nhập số điện thoại!', type='warning')
                return
            ui.notify(f"Thông tin đã lưu: {phone_input.value}")

        ui.button('Nhập').classes('px-6 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 w-full').on('click',
                                                                                                          submit)

    columns = [
        {'name': 'Số điện thoại', 'label': 'Số điện thoại', 'field': 'Số điện thoại', 'align': 'right'},
        {'name': 'Đường dẫn session', 'label': 'Đường dẫn session', 'field': 'Đường dẫn session', 'align': 'right'},
        {'name': 'Ngày tạo', 'label': 'Ngày tạo', 'field': 'Ngày tạo', 'align': 'right'},
    ]
    rows = [
        {'id': 0, 'Số điện thoại':'0912345678', 'Đường dẫn session': 'C:\\Users\\admin\\Desktop\\88101322355086\\35b42bde-55ed-4e38-8ac8-08f200bc1ebb\\+8801322355086',
         'Ngày tạo': datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        {'id': 1, 'Số điện thoại':'0912345678', 'Đường dẫn session': 'C:\\Users\\admin\\Desktop\\88101322355086\\35b42bde-55ed-4e38-8ac8-08f200bc1ebb\\+8801322355086',
         'Ngày tạo': datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
    ]

    def add_row() -> None:
        new_id = max((dx['id'] for dx in rows), default=-1) + 1
        new_row = {'id': new_id,'Số điện thoại':'0912345678', 'Đường dẫn session': 'C:\\Users\\admin\\Desktop\\88101322355086\\35b42bde-55ed-4e38-8ac8-08f200bc1ebb\\+8801322355086',
                   'Ngày tạo': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        rows.append(new_row)
        ui.notify(f'Added new row with ID {new_id}')
        table.update()

    def rename(e: events.GenericEventArguments) -> None:
        for row in rows:
            if row['id'] == e.args['id']:
                row.update(e.args)
        ui.notify('Cập nhật thành công!')
        table.update()

    def delete(e: events.GenericEventArguments) -> None:
        rows[:] = [row for row in rows if row['id'] != e.args['id']]
        ui.notify(f'Xóa dòng ID {e.args["id"]}')
        table.update()

    table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
    table.add_slot('header', r'''
        <q-tr :props="props">
            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.label }}
            </q-th>
            <q-th auto-width />
        </q-tr>
    ''')
    table.add_slot('body', r'''
        <q-tr :props="props">
            <q-td key="Số điện thoại" :props="props">
                {{ props.row['Số điện thoại'] }}
                <q-popup-edit v-model="props.row['Số điện thoại']" v-slot="scope"
                    @update:model-value="() => $parent.$emit('rename', props.row)"></q-popup-edit>
            </q-td>
            <q-td key="Đường dẫn session" :props="props">
                <!-- Truncate text and display full path in tooltip -->
                <div class="relative group">
                    <span class="truncate" :title="props.row['Đường dẫn session']">
                        {{ props.row['Đường dẫn session'] }}
                    </span>
                    <div class="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-gray-800 text-white text-xs p-2 rounded">
                        {{ props.row['Đường dẫn session'] }}
                    </div>
                </div>
                <q-popup-edit v-model="props.row['Đường dẫn session']" v-slot="scope"
                    @update:model-value="() => $parent.$emit('rename', props.row)"></q-popup-edit>
            </q-td>
            <q-td key="Ngày tạo" :props="props">
                {{ props.row['Ngày tạo'] }}
            </q-td>
            <q-td auto-width>
                <q-btn size="sm" color="warning" round dense icon="delete"
                    @click="() => $parent.$emit('delete', props.row)" />
            </q-td>
        </q-tr>
    ''')
    with table.add_slot('bottom-row'):
        with table.cell().props('colspan=4').style(''):
            ui.button('Thêm dữ liệu', icon='add', on_click=add_row).classes(
                'w-full px-20 py-2 bg-blue-500 text-white rounded hover:bg-blue-600'
            )
    table.on('rename', rename)
    table.on('delete', delete)

# Serve static files
ui.run(
    native=True,
    reload=True,
    title="SessionFarm",
    host='127.0.0.1',
    port=8080,
)
