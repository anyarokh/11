# імпортую потрібні бібліотеки для інтерфейсу, роботи зі словниками wordnet і обробки файлів
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from nltk.corpus import wordnet as wn
import nltk
from operator import itemgetter
import os

# завантажую базу wordnet (якщо ще не завантажена)
nltk.download('wordnet')


# функція для обчислення відстані левенштейна між двома словами (тобто кількості змін для перетворення одного слова
# в інше)
def levenshtein(w1, w2):
    d = {}
    for i in range(-1, len(w1) + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len(w2) + 1):
        d[(-1, j)] = j + 1
    for i in range(len(w1)):
        for j in range(len(w2)):
            cost = 0 if w1[i] == w2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,
                d[(i, j - 1)] + 1,
                d[(i - 1, j - 1)] + cost
            )
    return d[(len(w1) - 1, len(w2) - 1)]


# функція для виводу означень слова
def print_definitions(word):
    synsets = wn.synsets(word, wn.NOUN)
    if not synsets:
        return f"No definitions found for '{word}'."
    result = f"Definitions for '{word}':\n"
    for synset in synsets:
        result += f"- {synset.definition()}\n"
    return result


# функція для виводу гіпонімів та гіперонімів слова (використовую тільки перший синсет)
def print_hyponyms_hypernyms(word):
    synsets = wn.synsets(word, wn.NOUN)
    if not synsets:
        return f"No semantic relations found for '{word}'."
    result = f"Hyponyms and Hypernyms for '{word}':\n"
    for synset in synsets[:1]:  # беремо перший для прикладу
        hyponyms = [h.name().split('.')[0] for h in synset.hyponyms()]
        hypernyms = [h.name().split('.')[0] for h in synset.hypernyms()]
        result += f"  Hyponyms: {', '.join(hyponyms[:5]) or 'None'}\n"
        result += f"  Hypernyms: {', '.join(hypernyms[:5]) or 'None'}\n"
    return result


# функція для обчислення трьох типів семантичної подібності між двома словами
def calculate_semantic_similarity(word1, word2):
    try:
        synset1 = wn.synsets(word1, wn.NOUN)[0]
        synset2 = wn.synsets(word2, wn.NOUN)[0]
        path = synset1.path_similarity(synset2)
        wu = synset1.wup_similarity(synset2)
        lch = synset1.lch_similarity(synset2)
        return f"Semantic similarity:\nPath: {path}\nWu-Palmer: {wu}\nLeacock-Chodorow: {lch}"
    except:
        return "Semantic similarity could not be computed."

# функція для пошуку найближчих слів за відстанню левенштейна серед списку слів
def dict_distance(word, word_list, num_words):
    distances = {}
    for w in word_list:
        if w:  # пропускаю порожні рядки
            dist = levenshtein(word.lower(), w.lower())
            distances[w] = dist
    sorted_words = sorted(distances.items(), key=itemgetter(1))
    return sorted_words[:num_words]


# клас для створення графічного інтерфейсу застосунку
class WordAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Word Analyzer with WordNet")
        self.file_words = []

        self.tab_control = ttk.Notebook(root)

        # створюю вкладку для аналізу слів
        self.analyze_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.analyze_tab, text="🔍 Analyzer")

        # створюю вкладку з поясненням методів
        self.explanation_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.explanation_tab, text="🧠 Explanation")

        self.tab_control.pack(expand=1, fill='both')

        # елементи вкладки аналізу
        self.label = tk.Label(self.analyze_tab, text="Enter a word:")
        self.label.pack()

        self.entry = tk.Entry(self.analyze_tab, width=30)
        self.entry.pack()

        self.load_btn = tk.Button(self.analyze_tab, text="Load Text File", command=self.load_file)
        self.load_btn.pack()

        self.analyze_btn = tk.Button(self.analyze_tab, text="Analyze Word", command=self.analyze_word)
        self.analyze_btn.pack()

        self.output = tk.Text(self.analyze_tab, height=25, width=80)
        self.output.pack()

        # елементи вкладки пояснення
        self.explanation_text = tk.Text(self.explanation_tab, wrap='word')
        self.explanation_text.pack(expand=1, fill='both')

        explanation = """🧠 Пояснення методів семантичної подібності

    Коли ви порівнюєте два слова, програма використовує три методи для оцінки їх семантичної близькості. Ось що вони означають:

    🔹 Path Similarity
    Що це таке: Вимірює кількість кроків у ієрархії WordNet між двома поняттями (синсетами).
    Як працює: Чим менше кроків, тим ближчі поняття.
    Значення: Від 0 до 1.
        1 — ідентичні поняття.
        0 — поняття дуже далекі або не пов'язані.
    📌 Приклад: dog і wolf мають високу path similarity, бо обидва — тварини з подібною семантикою.

    🔹 Wu-Palmer Similarity
    Що це таке: Оцінює схожість двох понять, враховуючи їхню спільну батьківську категорію (найближчий спільний предок у WordNet).
    Як працює: Порівнює глибину найменшого спільного предка та глибини обох понять.
    Значення: Від 0 до 1.
        1 — дуже близькі поняття.
    📌 Приклад: car і vehicle мають високу Wu-Palmer подібність, бо "car" — тип "vehicle".

    🔹 Leacock-Chodorow Similarity (LCH)
    Що це таке: Вимірює близькість двох понять на основі найкоротшого шляху між ними у WordNet і загальної глибини ієрархії.
    Як працює: Використовує логарифмічну формулу.
    Значення: Від ~0 до ~3.6 (чим вище, тим схожіші).
        Не працює, якщо поняття з різних ієрархій (наприклад, дієслово і іменник).
    📌 Приклад: cat і tiger мають LCH ≈ 2.77, бо обидва — хижаки.

    🔠 Відстань Левенштейна (Levenshtein Distance)
    Що це таке: Кількість змін (вставок, видалень або замін літер), які потрібно зробити, щоб перетворити одне слово в інше.
    Як працює: Чим менше число, тим схожіші слова за написанням.
    Значення: Додатні цілі числа.
    📌 Приклад:
        cat → cut: 1 заміна (a → u)
        book → back: 2 заміни (o→a, o→c)
    """

        self.explanation_text.insert(tk.END, explanation)
        self.explanation_text.config(state='disabled')  # блокую редагування

    # функція для завантаження файлу зі словами
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.file_words = [w.strip().lower() for w in content.split() if w.isalpha()]
                messagebox.showinfo("File Loaded", f"{len(self.file_words)} words loaded.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # функція для аналізу введеного слова
    def analyze_word(self):
        word = self.entry.get().strip()
        if not word:
            messagebox.showwarning("Input Error", "Please enter a word.")
            return
        self.output.delete('1.0', tk.END)

        output_text = print_definitions(word) + "\n"
        output_text += print_hyponyms_hypernyms(word) + "\n"

        # питання про друге слово для подібності
        word2 = simpledialog.askstring("Compare Words", "Enter another word for similarity comparison:")
        if word2:
            output_text += calculate_semantic_similarity(word, word2) + "\n"
            output_text += f"Levenshtein distance: {levenshtein(word, word2)}\n"

        # якщо файл завантажено — шукаю найближчі за написанням
        if self.file_words:
            closest = dict_distance(word, self.file_words, 8)
            output_text += "\nClosest words:\n"
            output_text += "\n".join([f"{w} (distance: {d})" for w, d in closest])
        else:
            output_text += "\nNo file loaded to search for closest words."

        self.output.insert(tk.END, output_text)


# запуск
if __name__ == "__main__":
    root = tk.Tk()
    app = WordAnalyzerApp(root)
    root.mainloop()
