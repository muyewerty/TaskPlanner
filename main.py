import json, time, os, threading
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from plyer import notification
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput

Window.size = (380, 650)

class CustomSpinner(BoxLayout):
    spinner_text = StringProperty("Нет")
    options = ListProperty(["Нет", "1 минута", "5 минут", "10 минут", "Другое"])

    def open_dropdown(self, *args):
        dropdown = DropDown()
        for option in self.options:
            btn = Button(text=option, size_hint_y=None, height='42dp')
            btn.bind(on_release=lambda btn: dropdown.select(btn.text))
            dropdown.add_widget(btn)

        dropdown.bind(on_select=self.on_dropdown_select)
        dropdown.open(self)

    def on_dropdown_select(self, instance, selection):
        if selection == "Другое":
            self.show_text_input()
        else:
            self.spinner_text = selection

    def show_text_input(self):
        self.clear_widgets()  # Очищаем текущий виджет
        text_input = TextInput(
            hint_text="Введите время в минутах...",
            multiline=False,
            size_hint=(1, None),
            height="42dp"
        )
        text_input.bind(on_text_validate=self.on_text_enter)
        self.add_widget(text_input)
        text_input.focus = True  # Устанавливаем фокус для удобного ввода

    def on_text_enter(self, instance):
        self.spinner_text = instance.text  # Обновляем текст
        self.clear_widgets()  # Убираем TextInput
        self.add_spinner_button()  # Восстанавливаем спиннер

    def add_spinner_button(self):
        btn = Button(
            text=self.spinner_text,
            size_hint=(1, None),
            height="42dp",
            on_release=self.open_dropdown
        )
        self.add_widget(btn)

# Элемент списка задач: содержит кнопку для просмотра/редактирования и кнопку для удаления
class TaskItem(BoxLayout):
    task_text = StringProperty("")

    def __init__(self, task_text, **kwargs):
        super().__init__(**kwargs)
        self.task_text = task_text
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = "60dp"
        self.spacing = 10

        # Кнопка для просмотра/редактирования задачи
        self.task_button = Button(
            text=task_text,
            size_hint=(1, None),  # Занимает всю ширину
            height="50dp",
            background_normal="",  # Отключаем стандартный фон
            background_color=(0.6, 0.5, 0.4, 0.5),  # Тёмно-бежевый цвет
            on_release=self.view_task
        )
        self.add_widget(self.task_button)
   
    def view_task(self, instance):
        app = App.get_running_app()
        app.edit_screen.open_task(self.task_text)

# Главный экран со списком задач
class MainScreen(Screen):
    tasks_file = "tasks.json"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(lambda dt: self.load_tasks(), 0)

    def load_tasks(self):
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                for task in tasks:
                    self.add_task(task)
            except Exception as e:
                print("Ошибка загрузки задач:", e)

    def save_tasks(self):
        tasks = [child.task_text for child in self.ids.task_list.children if hasattr(child, 'task_text')]
        try:
            with open(self.tasks_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Ошибка сохранения задач:", e)

    def add_task(self, task_text, save=True):
        if not task_text.strip():
            return
        task_item = TaskItem(task_text=task_text)
        self.ids.task_list.add_widget(task_item)
        if save:
            self.save_tasks()

# Экран для редактирования или добавления задачи
class EditScreen(Screen):
    task_text = StringProperty("")

    def open_task(self, task_text):
        self.task_text = task_text
        self.ids.edit_text.text = task_text
        self.manager.current = "edit"

    def save_task(self):
        new_text = self.ids.edit_text.text
        # Получаем выбранное значение из кастомного спиннера
        timer_value = self.ids.custom_spinner.spinner_text
        app = App.get_running_app()
        main_screen = app.main_screen

        if self.task_text:
            for child in main_screen.ids.task_list.children:
                if hasattr(child, 'task_text') and child.task_text == self.task_text:
                    child.task_text = new_text
                    child.task_button.text = new_text
                    break
            else:
                main_screen.add_task(new_text)
        else:
            main_screen.add_task(new_text)

        main_screen.save_tasks()
        self.manager.current = "main"

        # Если выбрано напоминание, запускаем отдельный поток (если значение содержит число)
        if timer_value != "Нет" and timer_value:
            try:
                minutes = int(timer_value.split()[0])
                threading.Thread(target=self.set_reminder, args=(new_text, minutes)).start()
            except Exception as e:
                print("Неверное значение таймера:", e)

    def set_reminder(self, task_text, minutes):
        time.sleep(minutes * 60)
        notification.notify(
            title="Напоминание",
            message=f"Пора выполнить задачу: {task_text}",
            timeout=10
        )

    def delete_task(self):
        app = App.get_running_app()
        main_screen = app.main_screen
        for child in list(main_screen.ids.task_list.children):
            if hasattr(child, 'task_text') and child.task_text == self.task_text:
                main_screen.ids.task_list.remove_widget(child)
                self.manager.current = "main"
                break
        main_screen.save_tasks()

# Основное приложение
class TaskPlannerApp(App):
    def build(self):
        sm = ScreenManager()
        self.main_screen = MainScreen(name="main")
        self.edit_screen = EditScreen(name="edit")
        sm.add_widget(self.main_screen)
        sm.add_widget(self.edit_screen)
        return sm

if __name__ == '__main__':
    TaskPlannerApp().run()
