import re
from datetime import datetime

class TextProcessor:
    def __init__(self):
        # Паттерны для поиска терминов и определений
        self.term_patterns = [
            r'«([^»]+)»',  # Текст в кавычках
            r'\b[А-Я][а-я]+(?:\s+[А-Я][а-я]+)*\b',  # Слова с заглавной буквы
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Английские слова с заглавной буквы
        ]
        self.definition_pattern = r'[-—]\s*([^-—]+?)(?=[-—]|$)|\(([^)]+)\)'
        self.formula_pattern = r'\$(.+?)\$'
        
    def extract_terms(self, text):
        """Извлекает термины и определения из текста"""
        terms = []
        
        # Разбиваем текст на предложения
        sentences = re.split('[.!?]', text)
        
        for sentence in sentences:
            # Ищем определения
            definitions = re.findall(self.definition_pattern, sentence)
            
            # Ищем термины по всем паттернам
            for pattern in self.term_patterns:
                potential_terms = re.findall(pattern, sentence)
                
                for term in potential_terms:
                    if isinstance(term, tuple):
                        term = term[0]
                    if term and len(term) > 2:  # Игнорируем короткие термины
                        # Проверяем, не является ли термин служебным словом
                        if not self._is_common_word(term):
                            terms.append({
                                'term': term.strip(),
                                'definition': self._find_definition(term, definitions),
                                'type': 'term'
                            })
            
            # Ищем формулы
            formulas = re.findall(self.formula_pattern, sentence)
            for formula in formulas:
                terms.append({
                    'term': formula,
                    'type': 'formula'
                })
        
        # Удаляем дубликаты, сохраняя порядок
        unique_terms = []
        seen = set()
        for term in terms:
            term_key = (term['term'], term.get('definition'))
            if term_key not in seen:
                seen.add(term_key)
                unique_terms.append(term)
        
        return unique_terms
    
    def _find_definition(self, term, definitions):
        """Ищет определение для термина"""
        for definition in definitions:
            if isinstance(definition, tuple):
                definition = ' '.join(d for d in definition if d)
            if definition and term.lower() in definition.lower():
                return definition.strip()
        return None
    
    def _is_common_word(self, term):
        """Проверяет, является ли слово служебным"""
        common_words = {
            'Это', 'Также', 'Таким', 'Образом', 'Например', 'Далее',
            'Затем', 'Потом', 'Сначала', 'Поэтому', 'Однако',
            'The', 'This', 'That', 'These', 'Those', 'Then'
        }
        return term.strip() in common_words 

    def format_transcript(self, text, title=None):
        """Форматирует текст конспекта в красивый Markdown"""
        current_date = datetime.now().strftime('%d.%m.%Y %H:%M')
        
        # Извлекаем термины и определения
        terms = self.extract_terms(text)
        
        # Форматируем заголовок
        formatted_text = []
        formatted_text.append("# " + (title or f"Конспект лекции от {current_date}"))
        formatted_text.append("")  # Пустая строка после заголовка
        
        # Добавляем оглавление
        formatted_text.append("## Содержание")
        formatted_text.append("1. [Основной текст](#основной-текст)")
        if terms:
            formatted_text.append("2. [Термины и определения](#термины-и-определения)")
            if any(term['type'] == 'formula' for term in terms):
                formatted_text.append("3. [Формулы](#формулы)")
        formatted_text.append("")
        
        # Добавляем основной текст
        formatted_text.append("## Основной текст")
        formatted_text.append("")
        
        # Разбиваем текст на абзацы и форматируем
        paragraphs = text.split('\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                # Выделяем термины жирным
                for term in terms:
                    if term['type'] == 'term':
                        paragraph = re.sub(
                            rf"\b{re.escape(term['term'])}\b",
                            f"**{term['term']}**",
                            paragraph
                        )
                formatted_text.append(paragraph)
                formatted_text.append("")  # Пустая строка между абзацами
        
        # Добавляем секцию с терминами
        if terms:
            formatted_text.append("## Термины и определения")
            formatted_text.append("")
            
            # Сначала добавляем термины с определениями
            terms_with_defs = [t for t in terms if t['type'] == 'term' and t.get('definition')]
            if terms_with_defs:
                for term in terms_with_defs:
                    formatted_text.append(f"* **{term['term']}** — {term['definition']}")
                formatted_text.append("")
            
            # Затем термины без определений
            terms_without_defs = [t for t in terms if t['type'] == 'term' and not t.get('definition')]
            if terms_without_defs:
                formatted_text.append("### Упомянутые термины")
                formatted_text.append("")
                for term in terms_without_defs:
                    formatted_text.append(f"* **{term['term']}**")
                formatted_text.append("")
            
            # Добавляем формулы в отдельную секцию
            formulas = [t for t in terms if t['type'] == 'formula']
            if formulas:
                formatted_text.append("## Формулы")
                formatted_text.append("")
                for formula in formulas:
                    formatted_text.append(f"* ${formula['term']}$")
                formatted_text.append("")
        
        return "\n".join(formatted_text) 