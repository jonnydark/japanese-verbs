# -*- coding: utf-8 -*-
import unittest
import random
import mock  # TODO make this import conditional for Python 3 compatibility
from controllers.vtestcontroller import VerbTestController
import lib.verbs as verbs
import lib.database as database
import lib.quiz as quiz
from views.interface import QuizView


#TODO - Make this test run with mock data
@unittest.skipIf(
    not database.is_initialized(database.DEFAULT_DATABASE_PATH),
    "Database not initialized, need install before running this suite")
class TestVerbTestController(unittest.TestCase):

    def test_construction(self):
        ''' temporary test just to make sure that this all works'''
        controller = VerbTestController(QuizView())
        self.assertIsNotNone(controller)

    def test_start(self):
        view = self.MockQuizView()
        controller = VerbTestController(view)

        view.request_quiz_config = mock.MagicMock()

        controller.start()

        args = tuple(view.request_quiz_config.call_args)[0]
        self.assertEqual(view.request_quiz_config.call_count, 1)

        self.assertTrue(callable(args[0]),
                        "Controller did not provide view with valid callback")

    def test_full_quiz_cycle(self):
        ''' Arguably more a functional/integration test '''
        view = self.MockQuizView()
        controller = VerbTestController(view)

        number_of_questions = 10
        view.mock_config = {"number_of_questions": number_of_questions,
                            "inflections": dict()
                           }

        correct_answers = random.randrange(0, number_of_questions)

        # Patch view.ask_question to just call the callback with either
        # "correct" or "wrong" depending on how many times it's been
        # asked and the number of correct answers
        def mock_answer_question(q, callback):
            times_called = view.ask_question.call_count
            answer = "correct" if times_called <= correct_answers else "wrong"
            callback(answer)

        view.ask_question = mock.MagicMock(
            side_effect=mock_answer_question)

        # Patch view.handle_answer_result
        view.handle_answer_result = mock.MagicMock(
            side_effect=lambda ans, callback: callback())

        # Patch view.on_finish_quiz so we know it's called with the right data
        view.on_finish_quiz = mock.MagicMock()

        # Patching the controller methed make_question so the question answer
        # is always "correct"
        controller.make_question = lambda: {"data": object(),
                                            "asking_for": "Question",
                                            "answer": lambda x: "correct"}

        # Run the test
        controller.start()

        # Check controller asked the right number of questions
        self.assertEqual(view.ask_question.call_count, number_of_questions,
                         "Did not ask {} questions".format(number_of_questions))

        # Check controller sent the right number of results
        self.assertEqual(view.handle_answer_result.call_count,
                         number_of_questions)

        self.assertEqual(view.on_finish_quiz.call_count, 1)
        on_finish_args = tuple(view.on_finish_quiz.call_args)[0]
        self.assertEqual(on_finish_args[0].get("correct_answers", None),
                         correct_answers, "Controller reported wrong score")

    def test_build_questions(self):
        controller = VerbTestController(QuizView())

        Inf = verbs.Inflections
        # Yes I know this is bad practice as I am testing implementation
        # rather than interface. I'm sorry. If I think of a better way
        # later I'll fix it.
        controller.quiz_inflections = {
            Inf.PLAIN:
            [Inf.POLITE, Inf.NEGATIVE_POLITE]
        }

        question_dict = controller.make_question()

        data = question_dict.get("data")
        self.assertTrue(isinstance(data, verbs.Verb), "Data should be a verb")

        asking_for = question_dict.get("asking_for")
        self.assertTrue(asking_for in [Inf.POLITE, Inf.NEGATIVE_POLITE])

        answer = question_dict.get("answer")
        self.assertTrue(callable(answer), "answer param should be callable")
        self.assertEqual(answer(data), data.get_inflection(asking_for))

        predicate = question_dict.get("predicate")
        self.assertTrue(callable(predicate), "predicate should be callable")
        self.assertEqual(predicate(data), data.get_inflection(Inf.PLAIN))


    class MockQuizView(QuizView):
        def __init__(self):
            super(TestVerbTestController.MockQuizView, self).__init__()
            self.mock_config = None

        def do_request_config(self):
            self.set_quiz_config(self.mock_config)


if __name__ == "__main__":
    unittest.main()