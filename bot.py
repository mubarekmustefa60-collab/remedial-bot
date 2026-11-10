import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client
import os
from flask import Flask
import threading
import time 

# ================= 1. የመረጃ መቀበያ =================
BOT_TOKEN = "9296969504:AAGsg7ncwkfMV6Mn2eFs7JQLJXm3gJoMmJ4"
SUPABASE_URL = "https://rlkpxelwewazvtghqhhd.supabase.co"
SUPABASE_KEY = "sb_publishable_aCQcrqUsaGytogTK0Kom5g_yhmSjXKP"

VIP_GROUP_LINK = "https://t.me/+yQdJM7LxN8VmNWY0" 
SAMPLE_GROUP_LINK = "https://t.me/+39Ut1OlTHvdjYmQ0"

FREE_GROUP_ID = -1002492184485
STORAGE_GROUP_ID = -1004465909658
ADMIN_IDS = [6183608197, 8937172663]

bot = telebot.TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# ================= 2. ዳታቤዝ =================
def get_user(user_id):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if len(res.data) > 0:
        return res.data[0]
    else:
        new_user = {"user_id": user_id, "download_count": 0, "is_vip": False, "referred_count": 0}
        try:
            supabase.table("users").insert(new_user).execute()
        except:
            pass
        return new_user

def alert_admins(user_name, user_id, action):
    for admin in ADMIN_IDS:
        try:
            safe_name = str(user_name).replace("[", "").replace("]", "")
            bot.send_message(admin, f"🔔 **የምዝገባ እንቅስቃሴ!**\n\n👤 ተማሪ: [{safe_name}](tg://user?id={user_id})\n🎯 ምን እያደረገ ነው? : {action}", parse_mode="Markdown")
        except:
            pass

# ================= 3. የአድሚን ፓኔል (Admin Dashboard) =================
@bot.message_handler(commands=['admin', 'stats'], func=lambda message: message.from_user.id in ADMIN_IDS and message.chat.type == 'private')
def admin_panel(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 ሪፖርት ማያ 📈", callback_data="admin_stats"),
        InlineKeyboardButton("📝 ጥያቄ (Quiz) 🎯", callback_data="admin_quiz"),
        InlineKeyboardButton("📢 ወደ ግሩፕ ላክ 📌", callback_data="admin_broadcast_group"),
        InlineKeyboardButton("📩 ለተጠቃሚዎች ላክ 🚀", callback_data="admin_broadcast_users")
    )
    bot.send_message(message.chat.id, "👨‍💻 **የአድሚን መቆጣጠሪያ ፓኔል:**\n\nምን ማድረግ ይፈልጋሉ?", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    if call.from_user.id not in ADMIN_IDS:
        return
        
    if call.data == "admin_stats":
        bot.send_chat_action(call.message.chat.id, 'typing')
        try:
            res = supabase.table("users").select("*").execute()
            all_users = res.data
            total_users = len(all_users)
            vip_users = sum(1 for u in all_users if u.get('is_vip'))
            free_users = total_users - vip_users
            
            msg = (f"📊 **የቦቱ አጠቃላይ መረጃ (Stats)** 📊\n\n"
                   f"👥 **ጠቅላላ የጀመሩ ተማሪዎች (Total Users):** {total_users}\n"
                   f"🌟 **ክፍያ ፈፅመው የገቡ (VIP):** {vip_users}\n"
                   f"⏳ **እያሰቡ ያሉ (Free):** {free_users}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=msg, parse_mode="Markdown")
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Error: {e}", show_alert=True)
            
    elif call.data == "admin_quiz":
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                    text="📝 **ጥያቄዎን ይፃፉ:**\n\nበመጀመሪያ ጥያቄውን፣ በመቀጠል ደግሞ ምርጫዎቹን ከፊት ለፊታቸው ሰረዝ (-) በማድረግ ይፃፉ።\n\n*ለምሳሌ:*\nየትኛው ትክክል ነው?\n- ምርጫ ሀ\n- ምርጫ ለ\n\n(ለማቋረጥ /cancel ይበሉ)", 
                                    parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_quiz_broadcast)
        
    elif call.data == "admin_broadcast_group":
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                    text="📢 **ወደ ግሩፕ ማስታወቂያ ይላኩ:**\n\nማንኛውንም ፅሁፍ፣ ፎቶ ወይም ቪዲዮ አሁን ቢልኩልኝ ቀጥታ ዋናው ግሩፕ ላይ ልኬ **Pin 📌** አደርገዋለሁ።\n\n(ለማቋረጥ /cancel ይበሉ)", 
                                    parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_group_broadcast)

    elif call.data == "admin_broadcast_users":
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                    text="📩 **ወደ ተጠቃሚዎች Inbox ይላኩ:**\n\nማንኛውንም ፅሁፍ፣ ፎቶ ወይም ቪዲዮ አሁን ቢልኩልኝ ቦቱን ለጀመሩ **ለሁሉም ተማሪዎች** ቀጥታ በውስጥ መስመር እልካለሁ!\n\n(ለማቋረጥ /cancel ይበሉ)", 
                                    parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_user_broadcast)

# ወደ Inbox መላኪያ ኮድ
def process_user_broadcast(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "❌ የ Inbox ስርጭት ተቋርጧል።")
        return
        
    bot.send_message(message.chat.id, "⏳ መልዕክቱን ለሁሉም ተጠቃሚዎች በመላክ ላይ ነኝ... እባክዎ ይጠብቁ።")
    
    try:
        res = supabase.table("users").select("user_id").execute()
        users = res.data
        success = 0
        failed = 0
        
        for u in users:
            try:
                bot.copy_message(u['user_id'], message.chat.id, message.message_id)
                success += 1
            except:
                failed += 1
                
        bot.send_message(message.chat.id, f"✅ **ስርጭቱ ተጠናቋል!** 🚀\n\n🟢 በተሳካ ሁኔታ የደረሳቸው: {success}\n🔴 የከለከሉ (Block ያደረጉ): {failed}")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ ዳታቤዙን በማንበብ ላይ ችግር ተፈጥሯል: {e}")

# ወደ ግሩፕ መላኪያ (Pin ማድረጊያ)
def process_group_broadcast(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "❌ የማስታወቂያ ስርጭት ተቋርጧል።")
        return
        
    try:
        sent_msg = bot.copy_message(FREE_GROUP_ID, message.chat.id, message.message_id)
        bot.pin_chat_message(FREE_GROUP_ID, sent_msg.message_id)
        bot.send_message(message.chat.id, "✅ **ማስታወቂያው በተሳካ ሁኔታ ወደ ዋናው ግሩፕ ተልኮ Pin 📌 ተደርጓል!**")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ ማስታወቂያው ሲላክ ችግር ተፈጥሯል: {e}")

# የ Quiz ስርጭት መላኪያ
def process_quiz_broadcast(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "❌ የ Quiz ስርጭት ተቋርጧል።")
        return
        
    lines = message.text.split('\n')
    question = ""
    options = []
    
    for line in lines:
        if line.strip().startswith('-'):
            options.append(line.strip()[1:].strip())
        else:
            question += line + "\n"
            
    if not options:
        bot.send_message(message.chat.id, "⚠️ **ስህተት:** ምርጫዎቹን አላገኘሁም። እባክዎ ከፊት ለፊታቸው ሰረዝ (-) ያድርጉ።")
        return
        
    bot_info = bot.get_me()
    bot_link = f"https://t.me/{bot_info.username}?start=quiz"
    markup = InlineKeyboardMarkup(row_width=1)
    
    for opt in options:
        # ያሸበረቀች Button ለምርጫዎቹ
        markup.add(InlineKeyboardButton(text=f"🔘 {opt}", url=bot_link))
        
    try:
        sent_msg = bot.send_message(
            chat_id=FREE_GROUP_ID,
            text=f"📝 **የዛሬ ጥያቄ (Quiz):**\n\n{question.strip()}\n\n👇 **መልሱን ለመመለስ ከታች ያሉትን ምርጫዎች ይንኩ!**",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        bot.pin_chat_message(FREE_GROUP_ID, sent_msg.message_id)
        bot.send_message(message.chat.id, "✅ **ጥያቄው በ Poll መልክ ተልኮ Pin 📌 ተደርጓል!**")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {e}")

# ================= 4. ደረጃ 1: ሰላምታ እና መተዋወቅ =================
@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'private')
def start_funnel(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    user_data = get_user(user_id)
    args = message.text.split()
    
    if user_data.get('is_vip'):
        bot.send_message(user_id, f"👋 ሰላም የ Remedial Matrix VIP ተማሪ! ወደ ክላሱ ለመግባት ይህንን ሊንክ ይጠቀሙ፦\n{VIP_GROUP_LINK}")
        return

    if len(args) > 1 and args[1] == 'quiz':
        try:
            bot.send_dice(user_id, emoji='🎯')
            bot.send_chat_action(user_id, 'typing')
            time.sleep(1.5)
        except: pass
        intro_msg = (f"🎉 **በጣም ጎበዝ {first_name}! አሪፍ ሙከራ ነው!**\n\n"
                     "በትምህርትህ ላይ እንደዚህ አይነት ብዙ ጥያቄዎችን፣ የ Remedial Matrix ሞዴል ፈተናዎችን እና "
                     "አጫጭር ማብራሪያዎችን ማግኘት ትፈልጋለህ?\n\n")
    else:
        try:
            bot.send_dice(user_id, emoji='🎲')
            bot.send_chat_action(user_id, 'typing')
            time.sleep(1.5)
        except: pass
        intro_msg = (f"👋 ሰላም **{first_name}**! እንኳን ወደ **Remedial Matrix** በደህና መጣህ!\n\n"
                     "የ Remedial ትምህርት እና የፈተና ጊዜው አጭር በመሆኑ ብዙ ተማሪዎች ይጨነቃሉ። "
                     "ነገር ግን ትክክለኛውን የጥናት መንገድ ከተከተልክ በቀላሉ ማለፍ ትችላለህ!\n\n")
                     
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🧬 Natural Science 🟢", callback_data="stream_natural"),
        InlineKeyboardButton("🌍 Social Science 🟡", callback_data="stream_social")
    )
    
    msg = intro_msg + "እስኪ መጀመሪያ ልወቀህ... የትኛውን Stream ነህ የምትማረው? 👇"
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")

# ================= 5. ደረጃ 2: ችግርን መለየት እና ማጓጓት =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("stream_"))
def handle_stream_choice(call):
    user_id = call.from_user.id
    stream = call.data.split("_")[1]
    
    alert_admins(call.from_user.first_name, user_id, f"Stream መርጧል ({stream}) 📚")
    
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1.5)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎁 VIP ፓኬጁን አሳየኝ 🌟", callback_data="show_package"))
    
    if stream == "natural":
        msg = ("በጣም አሪፍ! 🧬 **Natural Science** ላይ በተለይ Physics እና Math ፈተናዎች ብዙ ተማሪዎችን ሲፈትኑ ይታያሉ።\n\n"
               "ግን አትጨነቅ! እኛ ጋ የሁሉንም ትምህርቶች (Math, Physics, Chemistry, Biology, English) "
               "ውስብስብ ጥያቄዎች እንዴት በቀላሉ መስራት እንደምትችል የምናሳይበት ልዩ ዘዴ አለን።\n\n"
               "ወደ VIP ክላሳችን ምን ምን እንዳዘጋጀንልህ ማየት ትፈልጋለህ?")
    else:
        msg = ("በጣም አሪፍ! 🌍 **Social Science** ላይ ሰፊ ንባብ የሚፈልጉት History፣ Geography እና በተለይ Mathematics "
               "ብዙ ተማሪዎችን ሲፈትኑ ይታያሉ።\n\n"
               "ግን አትጨነቅ! እኛ ጋ የሁሉንም ትምህርቶች (History, Geography, Math, English) "
               "ዋና ዋና ነጥቦች እና የፈተና አሰራር ስልቶችን የምናሳይበት ልዩ ዘዴ አለን።\n\n"
               "ወደ VIP ክላሳችን ምን ምን እንዳዘጋጀንልህ ማየት ትፈልጋለህ?")
               
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=msg, reply_markup=markup, parse_mode="Markdown")

# ================= 6. ደረጃ 3: መፍትሄ ማቅረብ እና Sample =================
@bot.callback_query_handler(func=lambda call: call.data == "show_package")
def show_vip_package(call):
    user_id = call.from_user.id
    
    alert_admins(call.from_user.first_name, user_id, "የ VIP ጥቅሞችን እያነበበ ነው... 🎁")
    
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1.5)
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👀 ነፃ የ Sample ትምህርቶችን እይ 💎", url=SAMPLE_GROUP_LINK),
        InlineKeyboardButton("💳 አሁኑኑ ልመዝገብ (300 ብር) 🚀", callback_data="pay_now")
    )
    
    msg = ("🏆 **የ Remedial Matrix VIP ክላስ** 🏆\n\n"
           "በክላሳችን ውስጥ ከተመዘገብክ እነዚህን ሁሉ ታገኛለህ፦\n\n"
           "✅ **ከ2015 እስከ 2018 E.C** የነበሩ የ Remedial Matrix ጥያቄዎች እና ሞዴል ፈተናዎች ከነ ሙሉ አሰራራቸው\n"
           "✅ ግልፅ የሆኑ ቪዲዮ ቲቶሪያሎች እና አጫጭር ኖቶች (በአማርኛ ማብራሪያ)\n"
           "✅ ራስህን የምትፈትሽባቸው Worksheets\n"
           "✅ 24/7 የጥያቄ እና መልስ ድጋፍ ከአስተማሪዎች ጋር\n\n"
           "⏱ **የፈተና ጊዜ በፍጥነት እየደረሰ ነው!** ቦታዎች ሳይሞሉ አሁኑኑ ተመዝግበህ ዝግጅትህን ጀምር!\n\n"
           "💰 **የክፍያ መጠን:** 300 ብር ብቻ (ለሙሉ ኮርሱ)")
           
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=msg, reply_markup=markup, parse_mode="Markdown")

# ================= 7. ደረጃ 4: ክፍያ እና ማሳመን =================
@bot.callback_query_handler(func=lambda call: call.data == "pay_now")
def show_payment_methods(call):
    user_id = call.from_user.id
    
    alert_admins(call.from_user.first_name, user_id, "የክፍያ አካውንቶችን እያየ ነው (ለመክፈል ተዘጋጅቷል)! 💳")
    
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1.5)
    
    msg = ("💳 **የክፍያ አማራጮች:**\n\n"
           "🔹 **Telebirr:** `0929698365`\n"
           "🔹 **CBE (ንግድ ባንክ):** `1000667301673`\n"
           "🔹 **Account name:** Mubarek Mustefa\n"
           "🔹 **የሚያስተላልፉት:** 300 ብር\n\n"
           "⚠️ **ትኩረት:** ክፍያውን ከፈፀሙ በኋላ የከፈሉበትን **ደረሰኝ (Screenshot)** "
           "ቀጥታ እዚሁ ቦት ላይ ይላኩልን (Upload ያድርጉ)።\n\n"
           "ወዲያውኑ እንዳረጋገጥን የ VIP ክላሱን መግቢያ ሊንክ እንልክልዎታለን! ጀግና ነህ/ነሽ፣ እንጠብቅሃለን! 💪")
           
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=msg, parse_mode="Markdown")

# ================= 8. ደረሰኝ ማረጋገጫ =================
@bot.message_handler(content_types=['photo'], func=lambda message: message.chat.type == 'private' and message.from_user.id not in ADMIN_IDS)
def handle_receipts(message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    if user_data.get('is_vip'):
        bot.reply_to(message, "✅ እርስዎ አስቀድመው የ VIP አባል ነዎት!")
        return 
        
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Approve 🟢", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Reject 🔴", callback_data=f"reject_{user_id}")
    )
    
    alert_admins(message.from_user.first_name, user_id, "ደረሰኝ (Screenshot) ልኳል! 🧾")
    
    for admin in ADMIN_IDS:
        try:
            bot.send_photo(
                admin, 
                message.photo[-1].file_id, 
                caption=f"🧾 **አዲስ ክፍያ መጥቷል!**\n\nየተማሪው ID: `{user_id}`\nስም: {message.from_user.first_name}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            pass
            
    bot.reply_to(message, "✅ ደረሰኝዎ ደርሶናል! በአጭር ጊዜ ውስጥ አድሚን አይቶ ክፍያውን ሲያረጋግጥ የ VIP ሊንክ ይደርስዎታል። መልካም ቆይታ!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_admin_decision(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "ይህ ለአድሚን ብቻ የተፈቀደ ነው!", show_alert=True)
        return
        
    action, student_id = call.data.split("_")
    student_id = int(student_id)
    
    if action == "approve":
        try:
            supabase.table("users").update({"is_vip": True}).eq("user_id", student_id).execute()
        except:
            pass
        bot.edit_message_caption("✅ **Approved! (ተረጋግጧል)**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(student_id, f"🎉 **እንኳን ደስ አሎት!** ክፍያዎ ተረጋግጧል።\n\nወደ VIP ክላስ ለመቀላቀል ይህንን ሊንክ ይጫኑ (ለማንም እንዳያጋሩ)፦\n{VIP_GROUP_LINK}")
    elif action == "reject":
        bot.edit_message_caption("❌ **Rejected! (ውድቅ ተደርጓል)**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(student_id, "❌ የላኩት ደረሰኝ ትክክል ስላልሆነ ውድቅ ተደርጓል። እባክዎ ትክክለኛ ደረሰኝ ይላኩ።")

# ================= 9. ለአዲስ ተጠቃሚዎች መምሪያ =================
@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type == 'private' and message.from_user.id not in ADMIN_IDS and not message.text.startswith('/'))
def guide_users(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 ወደ መጀመሪያ ተመለስ (Start)", callback_data="restart_flow"))
    
    msg = ("👋 ሰላም! ለቴሌግራም አዲስ ከሆኑ አያሳስብዎትም።\n\n"
           "እባክዎ እዚህ ጋ ዝም ብለው ፅሁፍ ከመፃፍ ይልቅ፣ <b>በመልዕክቱ መጨረሻ ላይ የተላኩልዎትን ቁልፎች (Buttons)</b> ይጫኑ።\n\n"
           "አሊያም ከታች ያለውን አዝራር ነክተው ከመጀመሪያ ይጀምሩ👇")
           
    bot.reply_to(message, msg, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "restart_flow")
def restart_flow(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.from_user.id, "እባክዎ ይህንን ይጫኑ 👉 /start")

# ================= 10. Web Server =================
@app.route('/')
def home():
    return "Remedial Sales Bot is running perfectly!"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
