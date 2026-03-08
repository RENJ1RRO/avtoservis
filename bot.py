import discord
from discord import app_commands
from discord.ui import View, Button
import asyncio
import logging
import time
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ID ролей и каналов
GUILD_ID = 1413836572541059113
GOVERNOR_ROLE_ID = 1413837529882562580
VICE_GOVERNOR_ROLE_ID = 1414036799231103121
ROLEPLAYER_ROLE_ID = 1427386845716680876
MERIA_ROLE_ID = 1414046676641120266
APPLICATIONS_CHANNEL_ID = 1417538990659342347
ANNOUNCEMENTS_CHANNEL_ID = 1414036742494748814
VERIFICATION_CHANNEL_ID = 1417544612381200619
MP_ROLE_ID = 1480164048451403856
MP_CHANNEL_ID = 1480164585385492610

# Словарь для хранения истории заявок пользователей
user_applications_history = {}

# Список всех ролей фракции, которые можно снимать
FACTION_ROLES = [
    1414037842275078236,  # Водитель
    1414037744526561351,  # Телохранитель
    1414037656366747680,  # Секретарь
    1414037530151620689,  # Председатель
    1414037473499283567,  # Адвокат
    1414037382608715816,  # Судья
    MERIA_ROLE_ID         # МЕРИЯ
]

class SelfRoleRemoveView(View):
    def __init__(self, user_id):
        super().__init__(timeout=300)  # 5 минут таймаут
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Проверяем, что кнопку нажимает тот же пользователь
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Вы не можете использовать эту кнопку! Эта функция только для самостоятельного снятия ролей.",
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="✅ Подтвердить снятие ролей", style=discord.ButtonStyle.danger, custom_id="self_remove_confirm")
    async def confirm_callback(self, interaction: discord.Interaction, button: Button):
        try:
            # Откладываем ответ
            await interaction.response.defer(ephemeral=True)
            
            guild = interaction.guild
            member = interaction.user
            
            # Получаем все роли фракции для снятия
            roles_to_remove = []
            for role_id in FACTION_ROLES:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    roles_to_remove.append(role)
            
            if not roles_to_remove:
                await interaction.followup.send(
                    "❌ У вас нет ролей фракции для снятия!",
                    ephemeral=True
                )
                return
            
            # Снимаем роли
            try:
                await member.remove_roles(*roles_to_remove)
            except Exception as e:
                logging.error(f"Ошибка при снятии ролей: {e}")
                await interaction.followup.send(
                    "❌ Произошла ошибка при снятии ролей! Обратитесь к администратору.",
                    ephemeral=True
                )
                return
            
            # Получаем названия снятых ролей
            removed_roles_names = [role.name for role in roles_to_remove]
            
            # Сбрасываем никнейм (убираем РП имя)
            try:
                original_nickname = member.display_name
                if " | " in original_nickname:
                    base_nickname = original_nickname.split(" | ")[0]
                    await member.edit(nick=base_nickname)
            except Exception as e:
                logging.error(f"Ошибка при сбросе никнейма: {e}")
            
            # Обновляем embed
            original_embed = interaction.message.embeds[0] if interaction.message.embeds else None
            if original_embed:
                new_embed = discord.Embed(
                    title="✅ Роли успешно сняты",
                    color=0x00ff00,
                    description="Вы самостоятельно сняли с себя все роли фракции."
                )
                
                # Копируем поля из оригинального embed
                for field in original_embed.fields:
                    new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                
                new_embed.add_field(name="✅ Статус", value="Роли сняты", inline=True)
                new_embed.add_field(name="🔻 Снятые роли", value=", ".join(removed_roles_names), inline=False)
                
                try:
                    await interaction.message.edit(embed=new_embed, view=None)
                except:
                    pass
            
            await interaction.followup.send(
                f"✅ Вы успешно сняли с себя роли фракции: {', '.join(removed_roles_names)}",
                ephemeral=True
            )
            
            # Удаляем сообщение через 30 секунд
            await asyncio.sleep(30)
            try:
                await interaction.message.delete()
            except:
                pass
                
        except Exception as e:
            logging.error(f"Ошибка в self_confirm_callback: {e}")
            try:
                await interaction.followup.send("❌ Произошла ошибка!", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary, custom_id="self_remove_cancel")
    async def cancel_callback(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Обновляем embed
            original_embed = interaction.message.embeds[0] if interaction.message.embeds else None
            if original_embed:
                new_embed = discord.Embed(
                    title="❌ Снятие ролей отменено",
                    color=0xff0000,
                    description="Вы отменили снятие ролей."
                )
                
                try:
                    await interaction.message.edit(embed=new_embed, view=None)
                except:
                    pass
            
            await interaction.followup.send(
                "✅ Снятие ролей отменено.",
                ephemeral=True
            )
            
            # Удаляем сообщение через 10 секунд
            await asyncio.sleep(10)
            try:
                await interaction.message.delete()
            except:
                pass
                
        except Exception as e:
            logging.error(f"Ошибка в cancel_callback: {e}")

class MpNotificationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔔 Получать уведомления об МП / Наборах",
        style=discord.ButtonStyle.primary,
        custom_id="mp_notify_button"
    )
    async def mp_button(self, interaction: discord.Interaction, button: Button):

        role = interaction.guild.get_role(MP_ROLE_ID)

        if not role:
            await interaction.response.send_message(
                "❌ Роль уведомлений не найдена.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                "🔕 Вы отключили уведомления об МП/Наборах.",
                ephemeral=True
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "🔔 Вы включили уведомления об МП/Наборах!",
                ephemeral=True
            )

class RoleApproveView(View):
    def __init__(self, role_id, user_id, role_name, server_nickname, rp_name, proof_url=None):
        super().__init__(timeout=None)
        self.role_id = int(role_id)
        self.user_id = user_id
        self.role_name = role_name
        self.server_nickname = server_nickname
        self.rp_name = rp_name
        self.proof_url = proof_url
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            # Получаем роли
            governor_role = interaction.guild.get_role(GOVERNOR_ROLE_ID)
            vice_governor_role = interaction.guild.get_role(VICE_GOVERNOR_ROLE_ID)
            roleplayer_role = interaction.guild.get_role(ROLEPLAYER_ROLE_ID)
            
            if not governor_role or not vice_governor_role or not roleplayer_role:
                logging.error("Одна из ролей не найдена на сервере")
                try:
                    await interaction.response.send_message(
                        "❌ Ошибка: не найдены необходимые роли на сервере!",
                        ephemeral=True
                    )
                except:
                    pass
                return False

            # Проверяем права
            has_permission = (
                governor_role in interaction.user.roles or 
                vice_governor_role in interaction.user.roles or
                roleplayer_role in interaction.user.roles
            )
            
            if not has_permission:
                try:
                    await interaction.response.send_message(
                        "❌ ты безправный, смирись",
                        ephemeral=True
                    )
                except:
                    pass
            
            return has_permission
            
        except Exception as e:
            logging.error(f"Ошибка в проверке прав: {e}")
            return False
    
    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success, custom_id="approve_role")
    async def approve_callback(self, interaction: discord.Interaction, button: Button):
        try:
            # Откладываем ответ чтобы избежать таймаута
            try:
                await interaction.response.defer(ephemeral=True)
            except:
                return
            
            guild = interaction.guild
            if not guild:
                return
            
            # Получаем пользователя
            try:
                member = await guild.fetch_member(self.user_id)
            except:
                # Создаем embed с ошибкой
                error_embed = discord.Embed(
                    title="❌ Пользователь не найден",
                    description="Пользователь, подавший заявку, не найден на сервере.",
                    color=0xff0000
                )
                try:
                    await interaction.message.edit(embed=error_embed, view=None)
                except:
                    pass
                return
            
            # Получаем роли
            role = guild.get_role(self.role_id)
            meria_role = guild.get_role(MERIA_ROLE_ID)
            
            if not role or not meria_role:
                error_embed = discord.Embed(
                    title="❌ Роль не найдена",
                    description="Запрашиваемая роль не найдена на сервере.",
                    color=0xff0000
                )
                try:
                    await interaction.message.edit(embed=error_embed, view=None)
                except:
                    pass
                return
            
            # Получаем список всех ролей, которые может выдавать бот
            bot_roles = [
                1414037842275078236,  # Водитель
                1414037744526561351,  # Телохранитель
                1414037656366747680,  # Секретарь
                1414037530151620689,  # Председатель
                1414037473499283567,  # Адвокат
                1414037382608715816   # Судья
            ]
            
            # Находим текущие роли пользователя из этого списка
            current_bot_roles = [r for r in member.roles if r.id in bot_roles]
            
            # Снимаем старые роли (кроме запрашиваемой)
            roles_to_remove = [r for r in current_bot_roles if r.id != self.role_id]
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove)
                except Exception as e:
                    logging.error(f"Ошибка при снятии ролей: {e}")
            
            # Выдаем новую роль и роль МЕРИИ
            try:
                await member.add_roles(role, meria_role)
            except Exception as e:
                logging.error(f"Ошибка при выдаче ролей: {e}")
                return
            
            # Меняем никнейм
            new_nickname = f"{self.server_nickname} | {self.rp_name}"
            try:
                await member.edit(nick=new_nickname[:32])
            except:
                pass
            
            # Обновляем историю заявок
            if self.user_id in user_applications_history:
                for app in user_applications_history[self.user_id]:
                    if (app['role_id'] == str(self.role_id) and 
                        app['server_nickname'] == self.server_nickname and
                        app['rp_name'] == self.rp_name and
                        app['status'] == 'pending'):
                        app['status'] = 'approved'
                        app['approved_by'] = interaction.user.id
                        app['approved_at'] = discord.utils.utcnow()
                        break
            
            # Обновляем embed
            original_embed = interaction.message.embeds[0] if interaction.message.embeds else None
            if not original_embed:
                return
                
            new_embed = discord.Embed(
                title="✅ Заявка принята",
                color=0x00ff00,
                description=f"Заявка была одобрена {interaction.user.mention}"
            )
            
            # Копируем поля из оригинального embed
            for field in original_embed.fields:
                if field.name not in ["📜 История заявок"]:
                    new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
            
            new_embed.add_field(name="✅ Статус", value="Одобрено", inline=True)
            new_embed.add_field(name="👨‍⚖️ Рассмотрено", value=interaction.user.mention, inline=True)
            new_embed.add_field(name="🔤 Новый ник", value=new_nickname, inline=False)
            
            removed_roles_text = ", ".join([r.name for r in roles_to_remove]) if roles_to_remove else "Нет"
            new_embed.add_field(name="🎭 Выданные роли", value=f"{self.role_name}, @𝓜𝓔𝓡𝓘𝓐", inline=False)
            if roles_to_remove:
                new_embed.add_field(name="🔻 Снятые роли", value=removed_roles_text, inline=False)
            
            # Редактируем сообщение
            try:
                await interaction.message.edit(embed=new_embed, view=None)
            except:
                pass
            
            # Уведомление пользователю
            try:
                notify_embed = discord.Embed(
                    title="🎉 Ваша заявка принята!",
                    description=f"Вам была выдана роль **{self.role_name}**\nДополнительно выдана роль @𝓜𝓔𝓡𝓘𝓐\nВаш никнейм изменен на: **{new_nickname}**",
                    color=0x00ff00
                )
                if roles_to_remove:
                    notify_embed.add_field(
                        name="🔻 Снятые роли", 
                        value=", ".join([r.name for r in roles_to_remove]), 
                        inline=False
                    )
                await member.send(embed=notify_embed)
            except:
                pass
            
            # Удаляем сообщение через 10 секунд
            await asyncio.sleep(10)
            try:
                await interaction.message.delete()
            except:
                pass
                
        except Exception as e:
            logging.error(f"Ошибка в approve_callback: {e}")
    
    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id="deny_role")
    async def deny_callback(self, interaction: discord.Interaction, button: Button):
        try:
            # Откладываем ответ
            try:
                await interaction.response.defer(ephemeral=True)
            except:
                return
            
            guild = interaction.guild
            
            # Обновляем историю заявок
            if self.user_id in user_applications_history:
                for app in user_applications_history[self.user_id]:
                    if (app['role_id'] == str(self.role_id) and 
                        app['server_nickname'] == self.server_nickname and
                        app['rp_name'] == self.rp_name and
                        app['status'] == 'pending'):
                        app['status'] = 'denied'
                        app['denied_by'] = interaction.user.id
                        app['denied_at'] = discord.utils.utcnow()
                        break
            
            # Обновляем embed
            original_embed = interaction.message.embeds[0] if interaction.message.embeds else None
            if not original_embed:
                return
                
            new_embed = discord.Embed(
                title="❌ Заявка отклонена, отклонение заявки не обсуждаеться",
                color=0xff0000,
                description=f"Заявка была отклонена {interaction.user.mention}"
            )
            
            # Копируем поля из оригинального embed
            for field in original_embed.fields:
                if field.name not in ["📜 История заявок"]:
                    new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
            
            new_embed.add_field(name="❌ Статус", value="Отклонено", inline=True)
            new_embed.add_field(name="👨‍⚖️ Рассмотрено", value=interaction.user.mention, inline=True)
            
            try:
                await interaction.message.edit(embed=new_embed, view=None)
            except:
                pass
            
            # Уведомление пользователю
            try:
                member = await guild.fetch_member(self.user_id)
                if member:
                    notify_embed = discord.Embed(
                        title="❌ Ваша заявка отклонена",
                        description=f"Ваша заявка на роль **{self.role_name}** была отклонена.",
                        color=0xff0000
                    )
                    await member.send(embed=notify_embed)
            except:
                pass
            
            # Удаляем сообщение через 10 секунд
            await asyncio.sleep(10)
            try:
                await interaction.message.delete()
            except:
                pass
                
        except Exception as e:
            logging.error(f"Ошибка в deny_callback: {e}")

class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        try:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            
            # Регистрируем персистентные View
            self.add_view(RoleApproveView(0, 0, "", "", ""))
            self.add_view(SelfRoleRemoveView(0))
            self.add_view(MpNotificationView())
            
            logging.info("✅ Бот успешно инициализирован!")
        except Exception as e:
            logging.error(f"❌ Ошибка в setup_hook: {e}")

    async def on_ready(self):
        logging.info(f'✅ Бот {self.user} успешно запущен!')
        logging.info(f'📊 Бот работает на {len(self.guilds)} серверах')
        
        try:
            await self.tree.sync()
            logging.info("✅ Команды синхронизированы")
        except Exception as e:
            logging.error(f"❌ Ошибка при синхронизации команд: {e}")
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="заявки на роли | /роль"
            )
        )

bot = MyBot()

# Словарь для сопоставления названий ролей с их ID
ROLE_MAPPING = {
    "водитель": "1414037842275078236",
    "телохранитель": "1414037744526561351", 
    "секретарь": "1414037656366747680",
    "председатель": "1414037530151620689",
    "адвокат": "1414037473499283567",
    "судья": "1414037382608715816"
}

@bot.tree.command(name="снятие_роли", description="Снять все роли фракции с себя (самостоятельно)")
async def self_remove_roles_command(interaction: discord.Interaction):
    try:
        # Сразу отвечаем на взаимодействие
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        
        # Проверяем, есть ли у пользователя роли фракции
        has_faction_roles = False
        current_faction_roles = []
        
        for role_id in FACTION_ROLES:
            role = interaction.guild.get_role(role_id)
            if role and role in member.roles:
                has_faction_roles = True
                current_faction_roles.append(role.name)
        
        if not has_faction_roles:
            await interaction.followup.send(
                "❌ У вас нет ролей фракции для снятия!",
                ephemeral=True
            )
            return
        
        # Создаем embed с подтверждением снятия ролей
        embed = discord.Embed(
            title="🔻 Подтверждение снятия ролей",
            color=0xff0000,
            description="**Внимание!** Вы собираетесь снять с себя все роли фракции.\n\nЭто действие **необратимо** и приведет к:\n• Снятию всех ролей фракции\n• Сбросу никнейма\n• Потере доступа к каналам фракции"
        )
        
        embed.add_field(name="👤 Пользователь", value=f"{member.mention} ({member.display_name})", inline=True)
        embed.add_field(name="🎭 Текущие роли фракции", value=", ".join(current_faction_roles) if current_faction_roles else "Нет", inline=False)
        embed.add_field(name="⏰ Время на подтверждение", value="5 минут", inline=True)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Нажмите кнопку ниже для подтверждения")
        
        # Отправляем сообщение с кнопками
        view = SelfRoleRemoveView(member.id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
    except Exception as e:
        logging.error(f"Ошибка в команде /снятие_роли: {e}")
        try:
            await interaction.followup.send(
                "❌ Произошла ошибка при создании запроса на снятие ролей!",
                ephemeral=True
            )
        except:
            pass

@bot.tree.command(name="роль", description="Подать заявку на получение роли")
@app_commands.describe(
    рп_имя="Ваше РП имя (например: Аллисер Хорниголд)",
    должность="Выберите должность из списка",
    файл="Прикрепите файл с изображением /pass (PNG, JPG, JPEG)"
)
@app_commands.choices(должность=[
    app_commands.Choice(name="🚗 Водитель", value="водитель"),
    app_commands.Choice(name="💂 Телохранитель", value="телохранитель"),
    app_commands.Choice(name="📝 Секретарь", value="секретарь"),
    app_commands.Choice(name="👑 Председатель", value="председатель"),
    app_commands.Choice(name="⚖️ Адвокат", value="адвокат"),
    app_commands.Choice(name="🧑‍⚖️ Судья", value="судья")
])
async def role_command(
    interaction: discord.Interaction, 
    рп_имя: str,
    должность: app_commands.Choice[str],
    файл: discord.Attachment
):
    try:
        # Сразу отвечаем на взаимодействие
        await interaction.response.defer(ephemeral=True)
        
        # Проверяем формат файла
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
        if not any(файл.filename.lower().endswith(ext) for ext in allowed_extensions):
            await interaction.followup.send(
                f"❌ Неподдерживаемый формат файла! Разрешенные форматы: {', '.join(allowed_extensions)}",
                ephemeral=True
            )
            return
        
        # Проверяем размер файла (максимум 8MB)
        if файл.size > 8 * 1024 * 1024:
            await interaction.followup.send(
                "❌ Файл слишком большой! Максимальный размер: 8MB",
                ephemeral=True
            )
            return
        
        # Получаем ID роли из выбранной должности
        role_id = ROLE_MAPPING.get(должность.value)
        role_name = должность.name.split(" ", 1)[1]  # Убираем эмодзи из названия
        
        if not role_id:
            await interaction.followup.send(
                "❌ Произошла ошибка при выборе роли!",
                ephemeral=True
            )
            return
        
        # Проверяем историю заявок пользователя
        user_id = interaction.user.id
        if user_id in user_applications_history:
            last_application = user_applications_history[user_id][-1]
            if last_application.get('status') == 'pending':
                await interaction.followup.send(
                    "❌ У вас уже есть активная заявка! Дождитесь рассмотрения предыдущей заявки или обратитесь к администратору.",
                    ephemeral=True
                )
                return
        
        # Добавляем заявку в историю
        if user_id not in user_applications_history:
            user_applications_history[user_id] = []
        
        application_data = {
            'timestamp': discord.utils.utcnow(),
            'role_id': role_id,
            'role_name': role_name,
            'server_nickname': interaction.user.display_name,
            'rp_name': рп_имя,
            'status': 'pending',
            'proof_url': файл.url
        }
        user_applications_history[user_id].append(application_data)
        
        # Создаем embed с заявкой
        embed = discord.Embed(
            title="📋 Новая заявка на роль",
            color=0x2b2d31,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="👤 Пользователь", value=f"{interaction.user.mention} ({interaction.user.display_name})", inline=True)
        embed.add_field(name="🆔 ID пользователя", value=interaction.user.id, inline=True)
        embed.add_field(name="🎭 Запрашиваемая роль", value=role_name, inline=True)
        embed.add_field(name="🎮 Ник на сервере", value=interaction.user.display_name, inline=True)
        embed.add_field(name="👤 РП имя", value=рп_имя, inline=True)
        embed.add_field(name="📋 Доказательства (/pass)", value=f"[Прикрепленное изображение]({файл.url})", inline=False)
        
        # Добавляем изображение в embed
        embed.set_image(url=файл.url)
        
        # Добавляем информацию о предыдущих заявках
        user_apps = user_applications_history[user_id]
        if len(user_apps) > 1:
            previous_apps = "\n".join([
                f"• {app['role_name']} ({app['timestamp'].strftime('%d.%m.%Y %H:%M')}) - {app['status']}"
                for app in user_apps[:-1][-3:]  # Последние 3 заявки (исключая текущую)
            ])
            embed.add_field(name="📜 История заявок", value=previous_apps, inline=False)
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Ожидает рассмотрения")
        
        # Отправляем заявку в канал
        channel = bot.get_channel(APPLICATIONS_CHANNEL_ID)
        if channel:
            view = RoleApproveView(
                role_id, 
                interaction.user.id, 
                role_name,
                interaction.user.display_name,
                рп_имя,
                файл.url
            )
            await channel.send(embed=embed, view=view)
            await interaction.followup.send(
                "✅ Ваша заявка успешно отправлена на рассмотрение!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Ошибка: канал для заявок не найден!",
                ephemeral=True
            )
            
    except Exception as e:
        logging.error(f"Ошибка в команде /роль: {e}")
        try:
            await interaction.followup.send(
                "❌ Произошла ошибка при обработке заявки!",
                ephemeral=True
            )
        except:
            pass

@bot.tree.command(name="доступные_роли", description="Показать список доступных ролей")
async def available_roles_command(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="💼 Доступные роли для заявок",
            description="Список всех ролей, на которые можно подать заявку:",
            color=0x2b2d31
        )
        
        roles_list = "\n".join([f"• {role.capitalize()}" for role in ROLE_MAPPING.keys()])
        embed.add_field(
            name="🎭 Роли",
            value=roles_list,
            inline=False
        )
        
        embed.add_field(
            name="📝 Как подать заявку",
            value="Используйте команду `/роль` и укажите:\n- Ваше РП имя\n- Должность из списка выше\n- Прикрепите файл с изображением /pass",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logging.error(f"Ошибка в команде /доступные_роли: {e}")
        try:
            await interaction.response.send_message("❌ Произошла ошибка!", ephemeral=True)
        except:
            pass

@bot.tree.command(name="панель_мп", description="Отправить панель уведомлений МП")
async def mp_panel(interaction: discord.Interaction):

    channel = bot.get_channel(MP_CHANNEL_ID)

    if not channel:
        await interaction.response.send_message(
            "❌ Канал не найден!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔔 Уведомления о МП и Наборах",
        description="Нажмите кнопку ниже чтобы получать уведомления о мероприятиях и наборах.",
        color=0x2b2d31
    )

    embed.add_field(
        name="Как это работает",
        value="Нажмите кнопку чтобы **включить уведомления**.\nНажмите ещё раз чтобы **отключить**.",
        inline=False
    )

    view = MpNotificationView()

    await channel.send(embed=embed, view=view)

    await interaction.response.send_message(
        "✅ Панель уведомлений отправлена!",
        ephemeral=True
    )    

def run_bot():
    TOKEN = "MTQyNjM0NDkzMjIwNTEzMzk3NA.GWbNk_.SVrGW7GI8GTL3EtUlgaJZMM9qJ5LefpG6-yc_I"
    
    # Автоперезапуск при ошибках
    while True:
        try:
            logging.info("🚀 Запуск бота...")
            bot.run(TOKEN)
        except KeyboardInterrupt:
            logging.info("🛑 Бот остановлен пользователем")
            break
        except Exception as e:
            logging.error(f"❌ Критическая ошибка: {e}")
            logging.info("🔄 Перезапуск бота через 60 секунд...")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()
