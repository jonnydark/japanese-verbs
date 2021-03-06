# -*- coding: utf-8 -*-
import random
import time
import threading
import lib.database as database
import lib.quiz as quiz
import lib.verbs as verbs


class VerbQuizController(object):

    def __init__(self, view):
        # probably should make db configurable
        self.db = database.Database(database.DEFAULT_DATABASE_PATH)
        self.view = view
        self.quiz = None
        self.quiz_inflections = dict()
        self.quiz_jlpt_level = None

    def start(self):
        self.view.start()
        self.view.request_quiz_config(self.on_have_quiz_config)

    def on_have_quiz_config(self, config):
        self.quiz_inflections = config["inflections"]
        self.quiz_jlpt_level = config.get("jlpt", 0)
        self.new_quiz(config["number_of_questions"])

    def new_quiz(self, number_of_questions):
        self.quiz = quiz.Quiz(number_of_questions, self.make_question)
        self.view.display_start_quiz()
        self.maybe_ask_question()

    def maybe_ask_question(self):
        if not self.quiz.finished():
            # Start it in its own thread to stop a horrible stack buildup
            t = threading.Thread(
                target=lambda:
                self.view.ask_question(self.quiz.ask_question(),
                                       self.handle_answer))
            t.start()
            t.join()
        else:
            self.view.on_finish_quiz({"quiz_length":
                                      self.quiz.length(),
                                      "correct_answers":
                                      self.quiz.answered_correctly()})

    def handle_answer(self, answer):
        result = self.quiz.answer_question(answer)
        threading.Thread(
            target=lambda:
            self.view.handle_answer_result(result, self.maybe_ask_question)
            ).start()

    def make_question(self):
        predicate = random.choice(list(self.quiz_inflections.keys()))
        # List comprehension to stop asking for itself
        possible_asks = [x for x in self.quiz_inflections[predicate]
                         if x != predicate]

        asking_for = random.choice(possible_asks)

        return {"data": verbs.Verb(**self.db.get_verb(
                                   jlpt=self.quiz_jlpt_level)),
                "asking_for": asking_for,
                "answer": lambda o: o.get_inflection(asking_for,
                                                     kanji=True, kana=True),
                "predicate": lambda o: o.get_inflection(predicate,
                                                        kanji=True, kana=True)
                }

    def wait_for_quiz_to_finish(self):
        if self.quiz is None:
            return
        # yes, this is a busy loop. I'm not especially happy about it either
        while not self.quiz.finished():
            time.sleep(0.1)


# Possibly put this in a general helper folder?
def make_bidirectional_verb_config(inflection_list):
    return {inf: [x for x in inflection_list if x != inf]
            for inf in inflection_list}


def make_monodirectional_verb_config(from_list, to_list):
    return {inf: to_list for inf in from_list}


class StandardConfig(object):
    ALL_PLAIN = 1
    ALL_POLITE = 2
    PLAIN_AND_POLITE = 3
    PLAIN_TO_TE_FORM = 4
    POLITE_TO_TE_FORM = 5
    CUSTOM = "C"

    @classmethod
    def All_readable_dict(cls):
        return {getattr(cls, c): c.replace("_", " ").title() for c in dir(cls)
                if not c.startswith("_")
                and not callable(getattr(cls, c))
                and not isinstance(getattr(cls, c), dict)
                and not isinstance(getattr(cls, c), list)}

    I = verbs.Inflections
    ALL_PLAIN_LIST = [I.PLAIN, I.NEGATIVE_PLAIN,
                      I.PAST_PLAIN, I.NEGATIVE_PAST_PLAIN]
    ALL_POLITE_LIST = [I.POLITE, I.NEGATIVE_POLITE,
                       I.PAST_POLITE, I.NEGATIVE_PAST_POLITE]
    PLAIN_AND_POLITE_LIST = ALL_PLAIN_LIST + ALL_POLITE_LIST
    TE_FORM_LIST = [I.TE_FORM]

    STANDARD_CONFIG_DICT = {
        ALL_PLAIN: make_bidirectional_verb_config(ALL_PLAIN_LIST),
        ALL_POLITE: make_bidirectional_verb_config(ALL_POLITE_LIST),
        PLAIN_AND_POLITE:
        make_bidirectional_verb_config(PLAIN_AND_POLITE_LIST),
        PLAIN_TO_TE_FORM:
        make_monodirectional_verb_config([I.PLAIN], TE_FORM_LIST),
        POLITE_TO_TE_FORM:
        make_monodirectional_verb_config([I.POLITE], TE_FORM_LIST)
    }

    @classmethod
    def get_config(cls, config_name):
        return cls.STANDARD_CONFIG_DICT.get(config_name, None)
