import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json
import os
from datetime import datetime, timedelta
import re
import random

VK_TOKEN = os.getenv('VK_TOKEN')

DATA_FILE = 'data.json'


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'editors': {},
        'news': [],
        'positions': {
            '1': {
                'name': 'Младший редактор',
                'limit': 100
            },
            '2': {
                'name': 'Редактор',
                'limit': 100
            },
            '3': {
                'name': 'Старший редактор',
                'limit': 10
            },
            '4': {
                'name': 'Заместитель главного редактора',
                'limit': 1
            },
            '5': {
                'name': 'Главный Редактор',
                'limit': 2
            },
            '6': {
                'name': 'Отвественный за отдел Редакторы',
                'limit': 999
            }
        },
        'pending_news': [],
        'next_news_id': 1
    }


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class VKNewsBot:

    def __init__(self, token):
        self.vk_session = vk_api.VkApi(token=token)
        self.vk = self.vk_session.get_api()

        try:
            groups = self.vk.groups.getById()
            self.group_id = groups[0]['id']
            group_name = groups[0].get('name', 'Неизвестно')
            print(f"✅ Определен ID группы: {self.group_id}")
            print(f"📌 Название группы: {group_name}")
        except Exception as e:
            print(f"❌ Ошибка получения ID группы: {e}")
            print("Проверьте, что токен принадлежит группе (не пользователю)")
            raise

        try:
            server_settings = self.vk.groups.getLongPollServer(
                group_id=self.group_id)
            print(f"✅ Long Poll Server настроен")
        except Exception as e:
            print(f"⚠️ Предупреждение Long Poll: {e}")
            print("❗ ВАЖНО: Включите Long Poll API в настройках группы:")
            print("   1. Управление → Работа с API → Long Poll API")
            print("   2. Включите Long Poll API")
            print("   3. Включите событие 'Входящие сообщения'")
            print(
                "   4. Включите 'Возможность для сообществ отправлять сообщения'"
            )

        self.longpoll = VkBotLongPoll(self.vk_session, self.group_id)
        self.data = load_data()
        print(f"✅ Бот успешно запущен!")
        print(f"📊 Загружено редакторов: {len(self.data.get('editors', {}))}")

    def send_message(self, peer_id, message):
        try:
            self.vk.messages.send(peer_id=peer_id,
                                  message=message,
                                  random_id=random.randint(0, 2**31))
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")

    def get_user_level(self, user_id):
        user_id = str(user_id)
        if user_id in self.data['editors']:
            return self.data['editors'][user_id]['level']
        return 0

    def check_permission(self, user_id, required_level):
        return self.get_user_level(user_id) >= required_level

    def get_user_info(self, user_id):
        try:
            user = self.vk.users.get(user_ids=user_id)[0]
            return f"{user['first_name']} {user['last_name']}"
        except:
            return f"ID{user_id}"

    def get_mention(self, text):
        patterns = [r'\[id(\d+)\|', r'@id(\d+)', r'vk\.com/id(\d+)']
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return None

    def cmd_start(self, peer_id, user_id, args):
        user_id_str = str(user_id)

        if user_id_str in self.data['editors']:
            editor = self.data['editors'][user_id_str]
            message = f"👋 Привет, {editor['name']}!\n\n"
            message += f"Вы уже зарегистрированы как редактор\n"
            message += f"Должность: {editor['position']} (уровень {editor['level']})\n\n"
            message += f"Используйте /help для просмотра доступных команд"
            self.send_message(peer_id, message)
            return

        if not self.data['editors']:
            user_name = self.get_user_info(user_id)
            now = datetime.now()
            next_promotion = now + timedelta(days=30)

            self.data['editors'][user_id_str] = {
                'name': user_name,
                'vk_id': user_id,
                'level': 6,
                'position': 'Бог',
                'warnings': 0,
                'bonuses': 0,
                'appointed_date': now.strftime('%d.%m.%Y'),
                'appointed_days': 0,
                'next_promotion': next_promotion.strftime('%d.%m.%Y'),
                'next_promotion_days': 30,
                'stats': {
                    'total_news': 0,
                    'rejected_news': 0,
                    'proposed_news': 0,
                    'warnings_received': 0
                }
            }

            save_data(self.data)

            message = f"🎉 Поздравляем, {user_name}!\n\n"
            message += f"Вы успешно зарегистрированы как первый администратор бота!\n"
            message += f"👤 Должность: Бог (уровень 6)\n"
            message += f"📅 Дата назначения: {now.strftime('%d.%m.%Y')}\n\n"
            message += f"У вас есть полный доступ ко всем командам.\n"
            message += f"Используйте /help для просмотра всех команд."

            self.send_message(peer_id, message)
        else:
            self.send_message(
                peer_id,
                "❌ Регистрация закрыта. Попросите администратора добавить вас командой /register"
            )

    def cmd_register(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для регистрации редакторов (требуется уровень 5)"
            )
            return

        if len(args) < 2:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /register @пользователь уровень\n\n"
            message += "Пример: /register @ivan 2\n"
            message += "Это зарегистрирует пользователя как редактора 2 уровня"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите пользователя которого хотите зарегистрировать:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /register @ivan 2"
            self.send_message(peer_id, message)
            return

        try:
            level = int(args[-1])
            if level < 1 or level > 6:
                raise ValueError
        except:
            self.send_message(peer_id, "❌ Уровень должен быть от 1 до 6")
            return

        target_name = self.get_user_info(target_id)
        position_name = self.data['positions'][str(level)]['name']

        now = datetime.now()
        next_promotion = now + timedelta(days=30)

        self.data['editors'][str(target_id)] = {
            'name': target_name,
            'vk_id': target_id,
            'level': level,
            'position': position_name,
            'warnings': 0,
            'bonuses': 0,
            'appointed_date': now.strftime('%d.%m.%Y'),
            'appointed_days': 0,
            'next_promotion': next_promotion.strftime('%d.%m.%Y'),
            'next_promotion_days': 30,
            'stats': {
                'total_news': 0,
                'rejected_news': 0,
                'proposed_news': 0,
                'warnings_received': 0
            }
        }

        save_data(self.data)
        self.send_message(
            peer_id,
            f"✅ {target_name} зарегистрирован как редактор!\n👤 Должность: {position_name} (уровень {level})\n📅 Дата назначения: {now.strftime('%d.%m.%Y')}"
        )

    def cmd_uplvl(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для повышения редакторов (требуется уровень 5)"
            )
            return

        if len(args) < 3:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /uplvl @пользователь уровень причина\n\n"
            message += "Пример: /uplvl @ivan 3 Хорошая работа\n"
            message += "Это повысит пользователя до 3 уровня"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите человека которого хотите повысить:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /uplvl @ivan 3 Хорошая работа"
            self.send_message(peer_id, message)
            return

        target_id = str(target_id)
        if target_id not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        try:
            new_level = int(args[1])
            if new_level < 1 or new_level > 6:
                raise ValueError
        except:
            self.send_message(peer_id, "❌ Уровень должен быть от 1 до 6")
            return

        reason = ' '.join(args[2:])
        editor = self.data['editors'][target_id]
        old_level = editor['level']
        old_position = editor['position']
        new_position = self.data['positions'][str(new_level)]['name']

        editor['level'] = new_level
        editor['position'] = new_position

        now = datetime.now()
        next_promotion = now + timedelta(days=30)
        editor['next_promotion'] = next_promotion.strftime('%d.%m.%Y')
        editor['next_promotion_days'] = 30

        save_data(self.data)

        message = f"⬆️ {editor['name']} повышен до {new_level} ({new_position})\n"
        message += f"Предыдущая должность: {old_position} (уровень {old_level})\n"
        message += f"📝 Причина: {reason}"

        self.send_message(peer_id, message)

    def cmd_downlvl(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для понижения редакторов (требуется уровень 5)"
            )
            return

        if len(args) < 3:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /downlvl @пользователь уровень причина\n\n"
            message += "Пример: /downlvl @ivan 1 Плохая работа\n"
            message += "Это понизит пользователя до 1 уровня"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите человека которого хотите понизить:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /downlvl @ivan 1 Плохая работа"
            self.send_message(peer_id, message)
            return

        target_id = str(target_id)
        if target_id not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        try:
            new_level = int(args[1])
            if new_level < 1 or new_level > 6:
                raise ValueError
        except:
            self.send_message(peer_id, "❌ Уровень должен быть от 1 до 6")
            return

        reason = ' '.join(args[2:])
        editor = self.data['editors'][target_id]
        old_level = editor['level']
        old_position = editor['position']
        new_position = self.data['positions'][str(new_level)]['name']

        editor['level'] = new_level
        editor['position'] = new_position

        save_data(self.data)

        message = f"⬇️ {editor['name']} понижен до {new_level} ({new_position})\n"
        message += f"Предыдущая должность: {old_position} (уровень {old_level})\n"
        message += f"📝 Причина: {reason}"

        self.send_message(peer_id, message)

    def cmd_warn(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 3):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для выдачи предупреждений (требуется уровень 3+)"
            )
            return

        if len(args) < 2:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /warn @пользователь причина\n\n"
            message += "Пример: /warn @ivan Опоздал со сдачей новости\n"
            message += "Это выдаст предупреждение пользователю"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите человека которому хотите выдать предупреждение:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /warn @ivan Опоздал со сдачей"
            self.send_message(peer_id, message)
            return

        target_id = str(target_id)
        if target_id not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        reason = ' '.join(args[1:])
        editor = self.data['editors'][target_id]
        editor['warnings'] += 1
        editor['stats']['warnings_received'] += 1

        save_data(self.data)

        message = f"⚠️ {editor['name']} получил предупреждение!\n"
        message += f"Выговоров: {editor['warnings']}/3\n"
        message += f"📝 Причина: {reason}\n"

        if editor['warnings'] >= 3:
            del self.data['editors'][target_id]
            save_data(self.data)
            message += f"\n🚫 {editor['name']} снят с должности за 3 предупреждения!"

        self.send_message(peer_id, message)

    def cmd_unwarn(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для снятия предупреждений (требуется уровень 5)"
            )
            return

        if len(args) < 1:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /unwarn @пользователь\n\n"
            message += "Пример: /unwarn @ivan\n"
            message += "Это снимет одно предупреждение с пользователя"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите человека которому хотите снять предупреждение:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /unwarn @ivan"
            self.send_message(peer_id, message)
            return

        target_id = str(target_id)
        if target_id not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        editor = self.data['editors'][target_id]
        if editor['warnings'] > 0:
            editor['warnings'] -= 1
            save_data(self.data)
            self.send_message(
                peer_id,
                f"✅ Предупреждение снято с {editor['name']}\nВыговоров: {editor['warnings']}/3"
            )
        else:
            self.send_message(peer_id,
                              f"ℹ️ У {editor['name']} нет предупреждений")

    def cmd_givebonus(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для управления бонусами (требуется уровень 5)"
            )
            return

        if len(args) < 2:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /givebonus @пользователь +/-количество\n\n"
            message += "Примеры:\n"
            message += "/givebonus @ivan +50 - добавить 50 бонусов\n"
            message += "/givebonus @ivan -20 - снять 20 бонусов"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите человека которому хотите изменить бонусы:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /givebonus @ivan +50"
            self.send_message(peer_id, message)
            return

        target_id = str(target_id)
        if target_id not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        try:
            bonus_change = int(args[-1])
        except:
            self.send_message(
                peer_id,
                "❌ Неверный формат бонусов. Используйте +число или -число")
            return

        editor = self.data['editors'][target_id]
        old_bonuses = editor.get('bonuses', 0)
        editor['bonuses'] = max(0, old_bonuses + bonus_change)

        save_data(self.data)

        if bonus_change > 0:
            message = f"✅ {editor['name']} получил +{bonus_change} бонусов!\n"
        else:
            message = f"⚠️ У {editor['name']} снято {abs(bonus_change)} бонусов\n"

        message += f"Было бонусов: {old_bonuses}\n"
        message += f"Стало бонусов: {editor['bonuses']}"

        self.send_message(peer_id, message)

    def cmd_giveprova(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 6):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для изменения прав доступа (требуется уровень 6)"
            )
            return

        if len(args) < 2:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /giveprova @пользователь уровень\n\n"
            message += "Пример: /giveprova @ivan 5\n"
            message += "Это изменит уровень доступа пользователя на 5"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите человека которому хотите изменить права:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /giveprova @ivan 5"
            self.send_message(peer_id, message)
            return

        target_id = str(target_id)
        if target_id not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        try:
            new_level = int(args[-1])
            if new_level < 1 or new_level > 6:
                raise ValueError
        except:
            self.send_message(peer_id, "❌ Уровень должен быть от 1 до 6")
            return

        editor = self.data['editors'][target_id]
        old_level = editor['level']
        old_position = editor['position']
        new_position = self.data['positions'][str(new_level)]['name']

        editor['level'] = new_level
        editor['position'] = new_position

        save_data(self.data)

        message = f"🔧 Права доступа {editor['name']} изменены!\n"
        message += f"Старая должность: {old_position} (уровень {old_level})\n"
        message += f"Новая должность: {new_position} (уровень {new_level})"

        self.send_message(peer_id, message)

    def cmd_kick(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для снятия редакторов (требуется уровень 5)")
            return

        if len(args) < 2:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /kick @пользователь причина\n\n"
            message += "Пример: /kick @ivan Неактивность\n"
            message += "Это снимет пользователя с должности редактора"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите человека которого хотите снять:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /kick @ivan Неактивность"
            self.send_message(peer_id, message)
            return

        target_id = str(target_id)
        if target_id not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        reason = ' '.join(args[1:])
        editor = self.data['editors'][target_id]
        editor_name = editor['name']

        del self.data['editors'][target_id]
        save_data(self.data)

        message = f"🚫 {editor_name} снят с должности редактора\n"
        message += f"📝 Причина: {reason}"

        self.send_message(peer_id, message)

    def cmd_news(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 1):
            self.send_message(peer_id, "❌ Вы не зарегистрированы как редактор")
            return

        if not self.data['news']:
            self.send_message(peer_id, "📰 Список новостей пуст")
            return

        message = f"📰 Список новостей ({len(self.data['news'])}):\n\n"
        for idx, news in enumerate(self.data['news'], 1):
            author_id = str(news.get('author_id', ''))
            author_name = self.data['editors'].get(author_id, {}).get(
                'name', 'Неизвестно')
            message += f"{idx}. {news['text'][:50]}...\n"
            message += f"   Автор: {author_name}\n"
            message += f"   Дата: {news.get('date', 'Не указана')}\n\n"

        self.send_message(peer_id, message)

    def cmd_addnews(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для добавления новостей (требуется уровень 5)"
            )
            return

        if not args:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /addnews текст новости\n\n"
            message += "Пример: /addnews Открытие нового раздела на сайте\n"
            message += "Это добавит новость в базу данных"
            self.send_message(peer_id, message)
            return

        news_text = ' '.join(args)

        news_item = {
            'id': self.data['next_news_id'],
            'text': news_text,
            'author_id': user_id,
            'date': datetime.now().strftime('%d.%m.%Y %H:%M')
        }

        self.data['news'].append(news_item)
        self.data['next_news_id'] += 1

        editor = self.data['editors'][str(user_id)]
        editor['stats']['total_news'] = editor['stats'].get('total_news',
                                                            0) + 1

        save_data(self.data)

        try:
            post = self.vk.wall.post(owner_id=-self.group_id,
                                     message=news_text,
                                     from_group=1)
            message = f"✅ Новость #{news_item['id']} добавлена и опубликована на стене!\n\n"
            message += f"📝 Текст: {news_text}"
            self.send_message(peer_id, message)
        except Exception as e:
            message = f"✅ Новость #{news_item['id']} добавлена в базу\n"
            message += f"⚠️ Ошибка публикации на стену: {e}\n\n"
            message += f"📝 Текст: {news_text}"
            self.send_message(peer_id, message)

    def cmd_delnews(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для удаления новостей (требуется уровень 5)")
            return

        if not args:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /delnews номер\n\n"
            message += "Пример: /delnews 3\n"
            message += "Это удалит новость под номером 3"
            self.send_message(peer_id, message)
            return

        try:
            news_index = int(args[0]) - 1
            if news_index < 0 or news_index >= len(self.data['news']):
                raise ValueError
        except:
            self.send_message(peer_id, "❌ Неверный номер новости")
            return

        deleted_news = self.data['news'].pop(news_index)
        save_data(self.data)

        message = f"🗑️ Новость удалена!\n\n"
        message += f"📝 Текст: {deleted_news['text']}"

        self.send_message(peer_id, message)

    def cmd_propose(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 1):
            self.send_message(peer_id, "❌ Вы не зарегистрированы как редактор")
            return

        if not args:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /propose текст новости\n\n"
            message += "Пример: /propose Предлагаю обсудить новую рубрику\n"
            message += "Это отправит новость на модерацию"
            self.send_message(peer_id, message)
            return

        news_text = ' '.join(args)

        proposal = {
            'id': len(self.data['pending_news']) + 1,
            'text': news_text,
            'author_id': user_id,
            'date': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'type': 'propose'
        }

        self.data['pending_news'].append(proposal)

        editor = self.data['editors'][str(user_id)]
        editor['stats']['proposed_news'] = editor['stats'].get(
            'proposed_news', 0) + 1

        save_data(self.data)

        message = f"✅ Предложение #{proposal['id']} отправлено на модерацию!\n\n"
        message += f"📝 Текст: {news_text}\n\n"
        message += "Редакторы 3+ уровня могут одобрить его командой /approve"

        self.send_message(peer_id, message)

    def cmd_pending(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 3):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для просмотра модерации (требуется уровень 3+)"
            )
            return

        if not self.data['pending_news']:
            self.send_message(peer_id, "📋 Нет новостей на модерации")
            return

        message = f"📋 Новости на модерации ({len(self.data['pending_news'])}):\n\n"
        for item in self.data['pending_news']:
            author_id = str(item.get('author_id', ''))
            author_name = self.data['editors'].get(author_id, {}).get(
                'name', 'Неизвестно')
            item_type = '📝 Предложение' if item.get(
                'type') == 'propose' else '📰 Новость'
            message += f"#{item['id']} {item_type}\n"
            message += f"Автор: {author_name}\n"
            message += f"Дата: {item.get('date', 'Не указана')}\n"
            message += f"Текст: {item['text'][:100]}...\n\n"

        message += "Используйте /approve ID или /reject ID причина"

        self.send_message(peer_id, message)

    def cmd_approve(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 3):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для одобрения (требуется уровень 3+)")
            return

        if not args:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /approve ID\n\n"
            message += "Пример: /approve 1\n"
            message += "Это одобрит предложенную новость с ID 1"
            self.send_message(peer_id, message)
            return

        try:
            proposal_id = int(args[0])
        except:
            self.send_message(peer_id, "❌ ID должен быть числом")
            return

        proposal = None
        for item in self.data['pending_news']:
            if item['id'] == proposal_id:
                proposal = item
                break

        if not proposal:
            self.send_message(peer_id,
                              f"❌ Предложение #{proposal_id} не найдено")
            return

        news_item = {
            'id': self.data['next_news_id'],
            'text': proposal['text'],
            'author_id': proposal['author_id'],
            'date': datetime.now().strftime('%d.%m.%Y %H:%M')
        }

        self.data['news'].append(news_item)
        self.data['next_news_id'] += 1
        self.data['pending_news'].remove(proposal)

        author_id = str(proposal['author_id'])
        if author_id in self.data['editors']:
            editor = self.data['editors'][author_id]
            editor['stats']['total_news'] = editor['stats'].get(
                'total_news', 0) + 1

        save_data(self.data)

        try:
            post = self.vk.wall.post(owner_id=-self.group_id,
                                     message=proposal['text'],
                                     from_group=1)
            message = f"✅ Предложение #{proposal_id} одобрено и опубликовано на стене!\n\n"
            message += f"📝 Текст: {proposal['text']}"
            self.send_message(peer_id, message)
        except Exception as e:
            message = f"✅ Предложение #{proposal_id} одобрено и добавлено в базу\n"
            message += f"⚠️ Ошибка публикации на стену: {e}\n\n"
            message += f"📝 Текст: {proposal['text']}"
            self.send_message(peer_id, message)

    def cmd_reject(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 3):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для отклонения (требуется уровень 3+)")
            return

        if len(args) < 2:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /reject ID причина\n\n"
            message += "Пример: /reject 1 Не соответствует тематике\n"
            message += "Это отклонит предложенную новость с ID 1"
            self.send_message(peer_id, message)
            return

        try:
            proposal_id = int(args[0])
        except:
            self.send_message(peer_id, "❌ ID должен быть числом")
            return

        reason = ' '.join(args[1:])

        proposal = None
        for item in self.data['pending_news']:
            if item['id'] == proposal_id:
                proposal = item
                break

        if not proposal:
            self.send_message(peer_id,
                              f"❌ Предложение #{proposal_id} не найдено")
            return

        self.data['pending_news'].remove(proposal)

        author_id = str(proposal['author_id'])
        if author_id in self.data['editors']:
            editor = self.data['editors'][author_id]
            editor['stats']['rejected_news'] = editor['stats'].get(
                'rejected_news', 0) + 1

        save_data(self.data)

        message = f"❌ Предложение #{proposal_id} отклонено\n\n"
        message += f"📝 Причина: {reason}\n"
        message += f"Текст: {proposal['text'][:100]}..."

        self.send_message(peer_id, message)

    def cmd_nw(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 1):
            self.send_message(peer_id, "❌ Вы не зарегистрированы как редактор")
            return

        if not args:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /nw текст новости\n\n"
            message += "Пример: /nw Открытие нового раздела\n\n"
            message += "Уровень 1-2: новость отправится на модерацию\n"
            message += "Уровень 3+: новость опубликуется сразу"
            self.send_message(peer_id, message)
            return

        news_text = ' '.join(args)
        user_level = self.get_user_level(user_id)

        if user_level >= 3:
            news_item = {
                'id': self.data['next_news_id'],
                'text': news_text,
                'author_id': user_id,
                'date': datetime.now().strftime('%d.%m.%Y %H:%M')
            }

            self.data['news'].append(news_item)
            self.data['next_news_id'] += 1

            editor = self.data['editors'][str(user_id)]
            editor['stats']['total_news'] = editor['stats'].get(
                'total_news', 0) + 1

            save_data(self.data)

            try:
                post = self.vk.wall.post(owner_id=-self.group_id,
                                         message=news_text,
                                         from_group=1)
                message = f"✅ Новость #{news_item['id']} опубликована на стене!\n\n"
                message += f"📝 Текст: {news_text}"
                self.send_message(peer_id, message)
            except Exception as e:
                message = f"✅ Новость #{news_item['id']} добавлена в базу\n"
                message += f"⚠️ Ошибка публикации на стену: {e}\n\n"
                message += f"📝 Текст: {news_text}"
                self.send_message(peer_id, message)
        else:
            proposal = {
                'id': len(self.data['pending_news']) + 1,
                'text': news_text,
                'author_id': user_id,
                'date': datetime.now().strftime('%d.%m.%Y %H:%M'),
                'type': 'nw'
            }

            self.data['pending_news'].append(proposal)

            editor = self.data['editors'][str(user_id)]
            editor['stats']['proposed_news'] = editor['stats'].get(
                'proposed_news', 0) + 1

            save_data(self.data)

            message = f"✅ Новость отправлена на модерацию!\n\n"
            message += f"📝 Текст: {news_text}\n\n"
            message += "Редакторы 3+ уровня могут одобрить её командой /accept"

            self.send_message(peer_id, message)

    def cmd_accept(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 3):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для одобрения (требуется уровень 3+)")
            return

        if not args:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /accept ID\n\n"
            message += "Пример: /accept 1\n"
            message += "Это одобрит новость с ID 1"
            self.send_message(peer_id, message)
            return

        try:
            proposal_id = int(args[0])
        except:
            self.send_message(peer_id, "❌ ID должен быть числом")
            return

        proposal = None
        for item in self.data['pending_news']:
            if item['id'] == proposal_id:
                proposal = item
                break

        if not proposal:
            self.send_message(peer_id, f"❌ Новость #{proposal_id} не найдена")
            return

        news_item = {
            'id': self.data['next_news_id'],
            'text': proposal['text'],
            'author_id': proposal['author_id'],
            'date': datetime.now().strftime('%d.%m.%Y %H:%M')
        }

        self.data['news'].append(news_item)
        self.data['next_news_id'] += 1
        self.data['pending_news'].remove(proposal)

        author_id = str(proposal['author_id'])
        if author_id in self.data['editors']:
            editor = self.data['editors'][author_id]
            editor['stats']['total_news'] = editor['stats'].get(
                'total_news', 0) + 1

        save_data(self.data)

        try:
            post = self.vk.wall.post(owner_id=-self.group_id,
                                     message=proposal['text'],
                                     from_group=1)
            message = f"✅ Новость #{proposal_id} одобрена и опубликована на стене!\n\n"
            message += f"📝 Текст: {proposal['text']}"
            self.send_message(peer_id, message)
        except Exception as e:
            message = f"✅ Новость #{proposal_id} одобрена и добавлена в базу\n"
            message += f"⚠️ Ошибка публикации на стену: {e}\n\n"
            message += f"📝 Текст: {proposal['text']}"
            self.send_message(peer_id, message)

    def cmd_cancel(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 3):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для отклонения (требуется уровень 3+)")
            return

        if len(args) < 2:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /cancel ID причина\n\n"
            message += "Пример: /cancel 1 Не соответствует формату\n"
            message += "Это отклонит новость с ID 1"
            self.send_message(peer_id, message)
            return

        try:
            proposal_id = int(args[0])
        except:
            self.send_message(peer_id, "❌ ID должен быть числом")
            return

        reason = ' '.join(args[1:])

        proposal = None
        for item in self.data['pending_news']:
            if item['id'] == proposal_id:
                proposal = item
                break

        if not proposal:
            self.send_message(peer_id, f"❌ Новость #{proposal_id} не найдена")
            return

        self.data['pending_news'].remove(proposal)

        author_id = str(proposal['author_id'])
        if author_id in self.data['editors']:
            editor = self.data['editors'][author_id]
            editor['stats']['rejected_news'] = editor['stats'].get(
                'rejected_news', 0) + 1

        save_data(self.data)

        message = f"❌ Новость #{proposal_id} отклонена\n\n"
        message += f"📝 Причина: {reason}\n"
        message += f"Текст: {proposal['text'][:100]}..."

        self.send_message(peer_id, message)

    def cmd_profile(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 1):
            self.send_message(peer_id, "❌ Вы не зарегистрированы как редактор")
            return

        target_id = user_id
        if args:
            mentioned_id = self.get_mention(' '.join(args))
            if mentioned_id:
                target_id = mentioned_id

        target_id_str = str(target_id)
        if target_id_str not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        editor = self.data['editors'][target_id_str]

        message = f"👤 Профиль редактора\n\n"
        message += f"Имя: {editor['name']}\n"
        message += f"Должность: {editor['position']} (уровень {editor['level']})\n"
        message += f"Дата назначения: {editor.get('appointed_date', 'Не указана')}\n"
        message += f"Предупреждений: {editor['warnings']}/3\n"
        message += f"Бонусов: {editor.get('bonuses', 0)}\n\n"

        message += f"📊 Статистика:\n"
        stats = editor.get('stats', {})
        message += f"Опубликовано новостей: {stats.get('total_news', 0)}\n"
        message += f"Предложено новостей: {stats.get('proposed_news', 0)}\n"
        message += f"Отклонено новостей: {stats.get('rejected_news', 0)}\n"
        message += f"Получено предупреждений: {stats.get('warnings_received', 0)}\n\n"

        message += f"📅 Дней до повышения: {editor.get('next_promotion_days', 30)}\n"
        message += f"Дата повышения: {editor.get('next_promotion', 'Не указана')}"

        self.send_message(peer_id, message)

    def cmd_editors(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 1):
            self.send_message(peer_id, "❌ Вы не зарегистрированы как редактор")
            return

        if not self.data['editors']:
            self.send_message(peer_id, "📋 Список редакторов пуст")
            return

        message = f"📋 Список редакторов ({len(self.data['editors'])}):\n\n"

        by_level = {}
        for editor_id, editor in self.data['editors'].items():
            level = editor['level']
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(editor)

        for level in sorted(by_level.keys(), reverse=True):
            position = self.data['positions'][str(level)]['name']
            message += f"📌 {position} (уровень {level}):\n"
            for editor in by_level[level]:
                message += f"  • {editor['name']} (Предупреждений: {editor['warnings']}/3)\n"
            message += "\n"

        self.send_message(peer_id, message)

    def cmd_positions(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 1):
            self.send_message(peer_id, "❌ Вы не зарегистрированы как редактор")
            return

        message = "📋 Список должностей:\n\n"
        for level in sorted(self.data['positions'].keys()):
            pos = self.data['positions'][level]
            message += f"Уровень {level}: {pos['name']}\n"
            message += f"  Лимит новостей: {pos['limit']}\n\n"

        self.send_message(peer_id, message)

    def cmd_setpos(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для настройки должностей (требуется уровень 5)"
            )
            return

        if len(args) < 3:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /setpos уровень название лимит\n\n"
            message += "Пример: /setpos 3 Редактор 15\n"
            message += "Это изменит название 3 уровня на 'Редактор' с лимитом 15 новостей"
            self.send_message(peer_id, message)
            return

        try:
            level = args[0]
            if level not in ['1', '2', '3', '4', '5', '6']:
                raise ValueError

            limit = int(args[-1])
            name = ' '.join(args[1:-1])

            self.data['positions'][level] = {'name': name, 'limit': limit}

            save_data(self.data)
            self.send_message(
                peer_id,
                f"✅ Должность уровня {level} настроена:\nНазвание: {name}\nЛимит: {limit}"
            )
        except:
            self.send_message(peer_id, "❌ Ошибка в параметрах команды")

    def cmd_setdolj(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для редактирования должностей (требуется уровень 5)"
            )
            return

        if len(args) < 3:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /setdolj уровень название лимит\n\n"
            message += "Примеры:\n"
            message += "/setdolj 1 Стажер 50\n"
            message += "/setdolj 3 Старший редактор 25\n\n"
            message += "Это изменит название должности для указанного уровня и установит лимит новостей"
            self.send_message(peer_id, message)
            return

        try:
            level = args[0]
            if level not in ['1', '2', '3', '4', '5', '6']:
                self.send_message(peer_id, "❌ Уровень должен быть от 1 до 6")
                return

            limit = int(args[-1])
            if limit < 0:
                self.send_message(peer_id,
                                  "❌ Лимит не может быть отрицательным")
                return

            name = ' '.join(args[1:-1])
            if not name:
                self.send_message(peer_id, "❌ Укажите название должности")
                return

            old_position = self.data['positions'][level].copy()

            self.data['positions'][level] = {'name': name, 'limit': limit}

            for editor_id, editor in self.data['editors'].items():
                if editor['level'] == int(level):
                    editor['position'] = name

            save_data(self.data)

            message = f"✅ Должность уровня {level} изменена!\n\n"
            message += f"Было: {old_position['name']} (лимит {old_position['limit']})\n"
            message += f"Стало: {name} (лимит {limit})\n\n"
            message += "Все редакторы этого уровня обновлены автоматически"

            self.send_message(peer_id, message)
        except ValueError:
            self.send_message(
                peer_id,
                "❌ Ошибка в параметрах команды. Проверьте правильность лимита (должно быть число)"
            )
        except Exception as e:
            self.send_message(peer_id, f"❌ Произошла ошибка: {str(e)}")

    def cmd_setday(self, peer_id, user_id, args):
        if not self.check_permission(user_id, 5):
            self.send_message(
                peer_id,
                "❌ У вас нет прав для изменения дней до повышения (требуется уровень 5)"
            )
            return

        if len(args) < 2:
            message = "❌ Неправильное использование команды!\n\n"
            message += "📝 Правильно: /setday @пользователь дни\n\n"
            message += "Примеры:\n"
            message += "/setday @ivan 60 - установить 60 дней до повышения\n"
            message += "/setday @maria 14 - установить 14 дней до повышения\n\n"
            message += "Это изменит количество дней до следующего повышения редактора"
            self.send_message(peer_id, message)
            return

        target_id = self.get_mention(' '.join(args))
        if not target_id:
            message = "❌ Не удалось найти пользователя!\n\n"
            message += "📝 Укажите редактора:\n"
            message += "• Упомяните его: @ivan\n"
            message += "• Или используйте ссылку: vk.com/id123456\n\n"
            message += "Пример: /setday @ivan 60"
            self.send_message(peer_id, message)
            return

        target_id = str(target_id)
        if target_id not in self.data['editors']:
            self.send_message(
                peer_id, "❌ Этот пользователь не зарегистрирован как редактор")
            return

        try:
            days = int(args[-1])
            if days < 0:
                self.send_message(
                    peer_id, "❌ Количество дней не может быть отрицательным")
                return
        except ValueError:
            self.send_message(
                peer_id, "❌ Неверный формат. Укажите количество дней числом")
            return
        except Exception as e:
            self.send_message(peer_id, f"❌ Ошибка: {str(e)}")
            return

        editor = self.data['editors'][target_id]
        old_days = editor.get('next_promotion_days', 30)

        now = datetime.now()
        next_promotion = now + timedelta(days=days)

        editor['next_promotion'] = next_promotion.strftime('%d.%m.%Y')
        editor['next_promotion_days'] = days

        save_data(self.data)

        message = f"✅ Дни до повышения изменены!\n\n"
        message += f"👤 Редактор: {editor['name']}\n"
        message += f"Было: {old_days} дней\n"
        message += f"Стало: {days} дней\n"
        message += f"Дата следующего повышения: {next_promotion.strftime('%d.%m.%Y')}"

        self.send_message(peer_id, message)

    def cmd_help(self, peer_id, user_id, args):
        level = self.get_user_level(user_id)

        message = f"📖 Доступные команды (ваш уровень: {level}):\n\n"

        if level == 0:
            message += "🔸 Вы не зарегистрированы как редактор\n\n"
            message += "/start - регистрация (первый пользователь получает уровень 6)\n"
            message += "/help - эта справка\n\n"
            message += "Если регистрация закрыта, попросите администратора добавить вас командой /register"
            self.send_message(peer_id, message)
            return

        if level >= 1:
            message += "🔹 Общие команды:\n"
            message += "/news - список новостей\n"
            message += "/profile [@пользователь] - профиль редактора\n"
            message += "/editors - список всех редакторов\n"
            message += "/positions - список должностей\n"
            message += "/propose текст - предложить новость\n"
            message += "/nw текст - добавить новость (уровень 1-2: на модерацию, 3+: сразу публикует)\n\n"

        if level >= 3:
            message += "🔸 Команды модератора (уровень 3+):\n"
            message += "/pending - новости на модерации\n"
            message += "/approve ID - одобрить новость\n"
            message += "/reject ID причина - отклонить новость\n"
            message += "/accept ID - одобрить новость через /nw\n"
            message += "/cancel ID причина - отклонить новость через /nw\n"
            message += "/warn @пользователь причина - выдать предупреждение\n\n"

        if level >= 5:
            message += "🔺 Команды руководства (уровень 5+):\n"
            message += "/register @пользователь уровень - регистрация редактора\n"
            message += "/uplvl @пользователь уровень причина - повышение\n"
            message += "/downlvl @пользователь уровень причина - понижение\n"
            message += "/kick @пользователь причина - снятие с должности\n"
            message += "/unwarn @пользователь - снять предупреждение\n"
            message += "/givebonus @пользователь +/-количество - управление бонусами\n"
            message += "/addnews текст - добавить новость\n"
            message += "/delnews номер - удалить новость\n"
            message += "/setpos уровень название лимит - настроить должность\n"
            message += "/setdolj уровень название лимит - изменить должность\n"
            message += "/setday @пользователь дни - установить дни до повышения\n\n"

        if level >= 6:
            message += "⚡ Команды уровня Бог (уровень 6):\n"
            message += "/giveprova @пользователь уровень - изменить права доступа\n\n"

        message += "/help - эта справка"

        self.send_message(peer_id, message)

    def process_message(self, event):
        try:
            text = event.obj.message['text'].strip()
            peer_id = event.obj.message['peer_id']
            user_id = event.obj.message['from_id']

            print(
                f"📨 Получено сообщение от ID{user_id} в чат {peer_id}: {text}")

            if not text:
                print("⚠️ Пустое сообщение, пропускаем")
                return

            parts = text.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            print(f"🔍 Команда: {command}, аргументы: {args}")
        except Exception as e:
            print(f"❌ Ошибка парсинга сообщения: {e}")
            return

        commands = {
            '/start': self.cmd_start,
            '/register': self.cmd_register,
            '/uplvl': self.cmd_uplvl,
            '/downlvl': self.cmd_downlvl,
            '/warn': self.cmd_warn,
            '/unwarn': self.cmd_unwarn,
            '/givebonus': self.cmd_givebonus,
            '/giveprova': self.cmd_giveprova,
            '/kick': self.cmd_kick,
            '/news': self.cmd_news,
            '/addnews': self.cmd_addnews,
            '/delnews': self.cmd_delnews,
            '/propose': self.cmd_propose,
            '/pending': self.cmd_pending,
            '/approve': self.cmd_approve,
            '/reject': self.cmd_reject,
            '/nw': self.cmd_nw,
            '/accept': self.cmd_accept,
            '/cancel': self.cmd_cancel,
            '/profile': self.cmd_profile,
            '/editors': self.cmd_editors,
            '/positions': self.cmd_positions,
            '/setpos': self.cmd_setpos,
            '/setdolj': self.cmd_setdolj,
            '/setday': self.cmd_setday,
            '/help': self.cmd_help
        }

        if command in commands:
            try:
                print(f"✅ Выполняю команду: {command}")
                commands[command](peer_id, user_id, args)
                print(f"✅ Команда {command} выполнена успешно")
            except Exception as e:
                print(f"❌ Ошибка выполнения команды {command}: {e}")
                import traceback
                traceback.print_exc()
                self.send_message(
                    peer_id,
                    f"❌ Произошла ошибка при выполнении команды: {str(e)}")
        else:
            print(f"⚠️ Неизвестная команда: {command}")

    def run(self):
        print("🤖 Бот запущен и слушает сообщения...")
        print("📝 Для остановки нажмите Ctrl+C")
        print("⏳ Ожидание событий от VK Long Poll...")

        event_count = 0
        try:
            for event in self.longpoll.listen():
                event_count += 1
                print(f"\n🔔 Событие #{event_count}: тип {event.type}")

                if event.type == VkBotEventType.MESSAGE_NEW:
                    print("📬 Новое сообщение!")
                    self.process_message(event)
                else:
                    print(f"ℹ️ Игнорируем событие типа: {event.type}")
        except KeyboardInterrupt:
            print("\n👋 Бот остановлен")
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    if not VK_TOKEN:
        print("❌ ОШИБКА: Не указан VK_TOKEN!")
        print("\n📝 Инструкция по настройке:")
        print("1. Создайте группу ВКонтакте (vk.com/groups)")
        print("2. Перейдите в Управление → Работа с API")
        print("3. Создайте ключ доступа с правами:")
        print("   - Управление сообществом")
        print("   - Сообщения сообщества")
        print("4. Включите Long Poll API в настройках:")
        print("   - Управление → Работа с API → Long Poll API")
        print("   - Включите Long Poll API")
        print("   - Отметьте 'Входящие сообщения' в типах событий")
        print("5. Добавьте токен в секреты проекта через кнопку 'Secrets'")
        print("6. Добавьте бота в беседу или пишите в сообщения группы")
        print(
            "\n💡 После добавления токена используйте команду /start для получения админки!"
        )
    else:
        try:
            bot = VKNewsBot(VK_TOKEN)
            print(
                "\n💡 Напишите боту команду /start чтобы получить права администратора!"
            )
            bot.run()
        except Exception as e:
            print(f"\n❌ Ошибка запуска бота: {e}")
            print("Проверьте правильность токена и настройки Long Poll API")
