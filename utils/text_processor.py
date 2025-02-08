import re
from datetime import datetime

class TextProcessor:
    def __init__(self):
        # Паттерны для поиска терминов и определений
        self.term_patterns = [
            r'«([^»]+)»',  # Текст в кавычках
            r'"([^"]+)"',  # Текст в двойных кавычках
            r'\b(?:[А-Я][а-я]+\s*){1,3}\b(?=\s*[-—]|\s*\(|\s*—\s*это)',  # Термины перед определением
            r'\b(?:[A-Z][a-z]+\s*){1,3}\b(?=\s*[-—]|\s*\(|\s*—\s*это)',  # Английские термины
        ]
        self.definition_patterns = [
            r'[-—]\s*([^-—.!?]+?)(?=[-—]|$|\.|!|\?)',  # Определение после тире
            r'\(([^)]+)\)',  # Определение в скобках
            r'—\s*это\s+([^.!?]+)',  # Определение после "это"
        ]
        self.formula_pattern = r'\$(.+?)\$'
        
        # Список игнорируемых слов
        self.common_words = {
            'Это', 'Также', 'Таким', 'Образом', 'Например', 'Далее',
            'Затем', 'Потом', 'Сначала', 'Поэтому', 'Однако', 'Итак',
            'The', 'This', 'That', 'These', 'Those', 'Then', 'Therefore',
            'При', 'Для', 'После', 'Перед', 'Когда', 'Если', 'Чтобы',
            'Здесь', 'Там', 'Где', 'Как', 'Какой', 'Который', 'Почему',
            'Каждый', 'Любой', 'Весь', 'Все', 'Многие', 'Некоторые'
        }
        
    def extract_terms(self, text):
        """Извлекает термины и определения из текста"""
        terms = []
        
        # Разбиваем текст на предложения
        sentences = re.split('[.!?]', text)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Ищем определения
            definitions = []
            for pattern in self.definition_patterns:
                found_defs = re.findall(pattern, sentence)
                definitions.extend([d.strip() for d in found_defs if d.strip()])
            
            # Ищем термины
            for pattern in self.term_patterns:
                potential_terms = re.findall(pattern, sentence)
                
                for term in potential_terms:
                    if isinstance(term, tuple):
                        term = term[0]
                    term = term.strip()
                    
                    if self._is_valid_term(term):
                        # Ищем определение для термина
                        definition = self._find_best_definition(term, definitions, sentence)
                        
                        terms.append({
                            'term': term,
                            'definition': definition,
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
        return self._remove_duplicates(terms)
    
    def _is_valid_term(self, term):
        """Проверяет, является ли строка допустимым термином"""
        if not term or len(term) < 3:
            return False
            
        # Проверяем, не является ли термин служебным словом
        if term in self.common_words:
            return False
            
        # Проверяем, не состоит ли термин только из цифр
        if term.replace('.', '').replace(',', '').isdigit():
            return False
            
        return True
    
    def _find_best_definition(self, term, definitions, sentence):
        """Находит наиболее подходящее определение для термина"""
        best_definition = None
        
        # Сначала ищем определение в списке найденных определений
        for definition in definitions:
            if term.lower() in definition.lower():
                return definition.strip()
        
        # Если не нашли, ищем определение после термина в предложении
        term_pos = sentence.find(term)
        if term_pos != -1:
            after_term = sentence[term_pos + len(term):].strip()
            for pattern in self.definition_patterns:
                match = re.search(pattern, after_term)
                if match:
                    return match.group(1).strip()
        
        return best_definition
    
    def _remove_duplicates(self, terms):
        """Удаляет дубликаты терминов, сохраняя лучшие определения"""
        unique_terms = {}
        
        for term in terms:
            term_key = term['term'].lower()
            
            if term_key not in unique_terms:
                unique_terms[term_key] = term
            elif term.get('definition') and not unique_terms[term_key].get('definition'):
                # Заменяем существующий термин, если у нового есть определение
                unique_terms[term_key] = term
        
        return list(unique_terms.values())

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