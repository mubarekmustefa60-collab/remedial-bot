import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client
import os
from flask import Flask
import threading

# ================= 1. የመረጃ መቀበያ (Configurations) =================
BOT_TOKEN = "9296969504:AAGsg7ncwkfMV6Mn2eFs7JQLJXm3gJoMmJ4"
SUPABASE_URL = "https://rlkpxelwewazvtghqhhd.supabase.co"
SUPABASE_KEY = "sb_publishable_aCQcrqUsaGytogTK0Kom5g_yhmSjXKP"

FREE_GROUP_ID = -1002492184485
STORAGE_GROUP_ID = -1004465909658
VIP_GROUP_LINK = "https://t.me/addlist/YourVIPLink" # የ VIP ክላስዎን መጋበዣ ሊንክ እዚህ ያስገቡ

ADMIN_IDS = [6183608197, 8937172663]

bot = telebot.TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

file_captions = {} # የፋይሉን ፅሁፍ (Caption) ለጊዜው ማቆያ

# ================= 2. ዳታቤዝ =================
def get_user(user_id):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if len(res.data) > 0:
        return res.data[0]
    else:
        new_user = {"user_id": user_id, "download_count": 0, "is_vip": False, "referred_count": 0}
        supabase.table("users").insert(new_user).execute()
        return new_user

# ================= 3. ፋይል ማዘጋጃ (ለአድሚን ብቻ Inbox ላይ) =================
@bot.message_handler(content_types=['document', 'video', 'photo', 'text'], func=lambda message: message.chat.type == 'private' and message.from_user.id in ADMIN_IDS)
def prepare_file_for_group(message):
    try:
        # 1. ፋይሉን ለደህንነት ወደ Storage Group መላክ
        stored_msg = bot.copy_message(STORAGE_GROUP_ID, message.chat.id, message.message_id)
        file_msg_id = stored_msg.message_id
        
        # 2. ፅሁፉን ማስታወስ
        if message.caption:
            caption = message.caption
        elif message.text:
            caption = message.text
        else:
            caption = "📚 አዲስ ማቴሪያል (Remedial Matrix)"
            
        file_captions[file_msg_id] = caption
        
        # 3. ለአድሚኑ መላኪያ ኮድ መስጠት
        bot.reply_to(message, f"✅ **ፋይሉ ተዘጋጅቷል!**\n\nዋናው ግሩፕ ላይ በሚፈልጉት ቶፒክ (ለምሳሌ Biology) ውስጥ ገብተው ይህንን አጭር ኮድ ይላኩ፦\n\n`/send {file_msg_id}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {e}")

# ================= 4. ቶፒክ ላይ ፖስት ማድረጊያ (ለአድሚን ብቻ ግሩፕ ላይ) =================
@bot.message_handler(commands=['send'], func=lambda message: message.chat.id == FREE_GROUP_ID and message.from_user.id in ADMIN_IDS)
def post_prepared_file(message):
    topic_id = message.message_thread_id
    
    # 1. አድሚኑ የፃፈውን አጭር ኮድ (/send 123) ማጥፋት
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
        
    args = message.text.split()
    if len(args) < 2:
        return
        
    file_msg_id = int(args[1])
    caption = file_captions.get(file_msg_id, "📚 አዲስ ማቴሪያል (Remedial Matrix)")
    
    # 2. Download እና View Buttons አዘጋጅቶ መልቀቅ
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📥 Download", callback_data=f"get_{file_msg_id}"),
        InlineKeyboardButton("👁 View", callback_data=f"get_{file_msg_id}")
    )
    
    bot.send_message(
        chat_id=FREE_GROUP_ID,
        text=f"📌 **{caption}**\n\nለማውረድ ወይም ለማየት ከታች ያሉትን ቁልፎች ይጠቀሙ👇",
        reply_markup=markup,
        message_thread_id=topic_id,
        parse_mode="Markdown"
    )

# ================= 5. ፋይል መላክ እና ቆጠራ (20 Limit) =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("get_"))
def handle_file_request(call):
    user_id = call.from_user.id
    file_msg_id = int(call.data.split("_")[1])
    
    try:
        bot.send_chat_action(user_id, 'typing')
    except Exception:
        bot.answer_callback_query(call.id, "⚠️ እባክዎ መጀመሪያ ወደ ቦቱ inbox ገብተው /start ይበሉ!", show_alert=True)
        return

    user_data = get_user(user_id)
    
    if user_data['is_vip']:
        bot.copy_message(user_id, STORAGE_GROUP_ID, file_msg_id, protect_content=True)
        bot.answer_callback_query(call.id, "✅ ፋይሉ በ Inbox ተልኳል!")
    else:
        count = user_data['download_count']
        if count < 20:
            new_count = count + 1
            supabase.table("users").update({"download_count": new_count}).eq("user_id", user_id).execute()
            bot.copy_message(user_id, STORAGE_GROUP_ID, file_msg_id, protect_content=True)
            remains = 20 - new_count
            bot.send_message(user_id, f"✅ ፋይሉ ተልኳል። (ነፃ ሙከራዎ {remains} ፋይሎች ቀርተውታል)")
            bot.answer_callback_query(call.id, "✅ ፋይሉ በ Inbox ተልኳል!")
        else:
            send_paywall(user_id)
            bot.answer_callback_query(call.id, "⚠️ የነፃ ፋይል ገደብዎ አልቋል!", show_alert=True)

# ================= 6. ክፍያ እና ግብዣ (Paywall) =================
def send_paywall(user_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💳 300 ብር ክፈል", callback_data="pay_money"),
        InlineKeyboardButton("👥 40 ሰው ጋብዝ", callback_data="invite_friends")
    )
    bot.send_message(user_id, "⚠️ **የነፃ ሙከራዎ (20 ፋይሎች) አልቋል!**\n\nእባክዎ ትምህርቱን ለመቀጠል ከታች ያለውን አማራጭ ይጠቀሙ።", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["pay_money", "invite_friends"])
def handle_paywall_options(call):
    user_id = call.from_user.id
    if call.data == "pay_money":
        msg = ("💳 **የክፍያ አማራጮች:**\n\n"
               "🔹 **Telebirr:** `0929698365`\n"
               "🔹 **CBE (ንግድ ባንክ):** `1000667301673`\n"
               "🔹 **Account name:** Mubarek Mustefa\n"
               "🔹 **የሚያስተላልፉት:** 300 ብር\n\n"
               "ከፍለው screenshot እዚህ 👇 ይላኩልን። ወዲያው አረጋግጠን ወደ ዋናው class (remedial special class) እናስገባዎታለን።")
        bot.send_message(user_id, msg, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        
    elif call.data == "invite_friends":
        bot_info = bot.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        user_data = get_user(user_id)
        current_ref = user_data['referred_count']
        msg = (f"👥 **የመጋበዣ ሊንክዎ:**\n\n{invite_link}\n\n"
               f"ይህንን ሊንክ በመላክ 40 ተማሪዎችን ወደ ቦቱ ይጋብዙ።\n"
               f"እስካሁን የጋበዙት: **{current_ref} / 40**")
        bot.send_message(user_id, msg, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

# ================= 7. ደረሰኝ ማረጋገጫ (ተማሪዎች ሲልኩ ብቻ) =================
@bot.message_handler(content_types=['photo'], func=lambda message: message.chat.type == 'private' and message.from_user.id not in ADMIN_IDS)
def handle_receipts(message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    if user_data['is_vip']:
        return 
        
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
    )
    
    for admin in ADMIN_IDS:
        try:
            bot.send_photo(
                admin, 
                message.photo[-1].file_id, 
                caption=f"🧾 **አዲስ ክፍያ!**\n\nየተማሪው ID: `{user_id}`\nስም: {message.from_user.first_name}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            pass
            
    bot.reply_to(message, "✅ ደረሰኝዎ ደርሶናል! በአጭር ጊዜ ውስጥ አድሚን አይቶ Approval ሲሰጥዎ መልዕክት ይደርስዎታል።")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_admin_decision(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "ይህ ለአድሚን ብቻ የተፈቀደ ነው!", show_alert=True)
        return
        
    action, student_id = call.data.split("_")
    student_id = int(student_id)
    
    if action == "approve":
        supabase.table("users").update({"is_vip": True}).eq("user_id", student_id).execute()
        bot.edit_message_caption("✅ **Approved!**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(student_id, f"🎉 እንኳን ደስ አሎት! ክፍያዎ ተረጋግጧል።\n\nወደ VIP ክላስ ለመቀላቀል ይህንን ይንኩ: {VIP_GROUP_LINK}")
    elif action == "reject":
        bot.edit_message_caption("❌ **Rejected!**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(student_id, "❌ የላኩት ደረሰኝ ትክክል ስላልሆነ ውድቅ ተደርጓል። እባክዎ ትክክለኛ ደረሰኝ ይላኩ።")

# ================= 8. መግቢያ እና Web Server =================
@bot.message_handler(commands=['start'])
def start_bot(message):
    user_id = message.from_user.id
    args = message.text.split()
    user_data = get_user(user_id)
    
    if len(args) > 1 and args[1].startswith("ref_"):
        inviter_id = int(args[1].split("_")[1])
        if inviter_id != user_id and user_data['download_count'] == 0:
            inviter_data = get_user(inviter_id)
            new_ref_count = inviter_data['referred_count'] + 1
            supabase.table("users").update({"referred_count": new_ref_count}).eq("user_id", inviter_id).execute()
            bot.send_message(inviter_id, f"🎉 አንድ ሰው በሊንክዎ ገብቷል! (ጠቅላላ የጋበዙት: {new_ref_count} / 40)")
            
            if new_ref_count >= 40:
                supabase.table("users").update({"is_vip": True}).eq("user_id", inviter_id).execute()
                bot.send_message(inviter_id, f"🏆 እንኳን ደስ አሎት! 40 ሰው ስለጋበዙ የ VIP አባል ሆነዋል። ሊንክ: {VIP_GROUP_LINK}")

    bot.reply_to(message, "👋 ሰላም! ይህ የ Remedial ማቴሪያሎች ማውረጃ ቦት ነው። ትምህርቶችን ከ ዋናው ግሩፕ ላይ ማውረድ ይችላሉ።\n\n⚠️ ማሳሰቢያ፡ ፋይሎችን ለማውረድ ቦቱ ላይ 'Start' ማለቶን እርግጠኛ ይሁኑ።")

@app.route('/')
def home():
    return "Remedial Bot is running successfully!"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
