def number_to_hebrew_words_female(num):
    """
    ממיר מספר (כולל עשרוני) לטקסט בעברית בלשון נקבה לקריינות.
    לדוגמה: 234.56 → 'מאתיים שלושים וארבע נקודה חמש שש'
    """
    num = round(num, 2)
    parts = str(num).split('.')
    int_part = int(parts[0])
    words = convert_integer_to_words_female(int_part)

    if len(parts) > 1 and int(parts[1]) != 0:
        decimal_digits = ' '.join([convert_digit_to_word_female(d) for d in parts[1]])
        words += f" נקודה {decimal_digits}"

    return words

def convert_integer_to_words_female(n):
    units = ["אפס", "אחת", "שתיים", "שלוש", "ארבע", "חמש", "שש", "שבע", "שמונה", "תשע"]
    tens = ["", "", "עשרים", "שלושים", "ארבעים", "חמישים", "שישים", "שבעים", "שמונים", "תשעים"]
    hundreds = ["", "מאה", "מאתיים", "שלוש מאות", "ארבע מאות", "חמש מאות", "שש מאות", "שבע מאות", "שמונה מאות", "תשע מאות"]

    if n == 0:
        return "אפס"

    result = []
    if n >= 1000:
        thousands = n // 1000
        n %= 1000
        if thousands == 1:
            result.append("אלף")
        elif thousands == 2:
            result.append("אלפיים")
        else:
            result.append(f"{convert_integer_to_words_female(thousands)} אלף")

    if n >= 100:
        result.append(hundreds[n // 100])
        n %= 100

    if n >= 20:
        result.append(tens[n // 10])
        n %= 10

    if 10 < n < 20:
        teens = {
            11: "אחת עשרה", 12: "שתים עשרה", 13: "שלוש עשרה", 14: "ארבע עשרה",
            15: "חמש עשרה", 16: "שש עשרה", 17: "שבע עשרה", 18: "שמונה עשרה", 19: "תשע עשרה"
        }
        result.append(teens[n])
        n = 0

    if 0 < n <= 10:
        result.append(units[n])

    return ' ו'.join([w for w in result if w])

def convert_digit_to_word_female(digit):
    digits = ["אפס", "אחת", "שתיים", "שלוש", "ארבע", "חמש", "שש", "שבע", "שמונה", "תשע"]
    return digits[int(digit)]
