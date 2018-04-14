import nltk

from app.criterias_calculation.controversy import Controversy
from app.criterias_calculation.emotion import Emotion
from app.criterias_calculation.factuality_opinion import FactualityOpinion
from app.criterias_calculation.readability import Readability
from app.criterias_calculation.score_normalization import ScoreNormalization
from app.criterias_calculation.sql_manager import SQLManager
from app.criterias_calculation.technicality import Technicality
from app.criterias_calculation.topicality import Topicality
from app.criterias_calculation.trust import Trust


def score_format(score):
    return round(score, 2)


def params_to_dict(params):
    dictionary = {}
    for p in params:
        dictionary[p[0]] = {'score': p[1], 'desc': p[2]}

    return dictionary


def tuple_to_params(sql_tuple):
    return [
        ['factuality', sql_tuple[2], sql_tuple[10], True],
        ['readability', sql_tuple[3], sql_tuple[11], False],
        ['emotion', sql_tuple[4], sql_tuple[12], True],
        ['opinion', sql_tuple[5], sql_tuple[13], True],
        ['controversy', sql_tuple[6], sql_tuple[14], True],
        ['trust', sql_tuple[7], sql_tuple[15], False],
        ['technicality', sql_tuple[8], sql_tuple[16], True],
        ['topicality', sql_tuple[9], sql_tuple[17], True]
    ]


class ScoreCalculation:

    def __init__(self, article, url):
        self.article = article
        self.url = url
        self.sql_manager = SQLManager()

        if self.sql_manager.article_exists(url):
            self.params = tuple_to_params(self.sql_manager.get_scores(url))
        else:
            self.calculate_criteria()

    def calculate_criteria(self):
        readability_score, readability_agreement_rate = Readability.get_score(self.article.text)
        controversy_score = Controversy.call(self.article)
        technicality_score = Technicality.get_score(self.article.text)
        trust_score, trust_confidence = Trust.call(self.url)
        fact_score, opinion_score, fact_sents, opinion_sents, nb_sents = FactualityOpinion.classify(self.article.text)
        emotion_score, nb_neg, nb_pos = Emotion.get_score(self.article.text)
        self.article.nlp()
        topicality_score = None

        self.params = [
            ['factuality', fact_score, None, True],
            ['readability', readability_score,
             "Agreement rate : {}%".format(score_format(readability_agreement_rate)), False],
            ['emotion', emotion_score, None, True],
            ['opinion', opinion_score, None, True],
            ['controversy', controversy_score, None, True],
            ['trust', score_format(trust_score),
             "Confidence score : {}%".format(score_format(trust_confidence)), False],
            ['technicality', technicality_score, None, True],
            ['topicality', topicality_score, None, True]
        ]

        self.sql_manager.insert_new_scores(self.url, params_to_dict(self.params))

    def get_normalized_params(self):
        """
        Return an params array with normalized score
        :return: params array with each item on the form :
                 [criterion_name, score, description, to_be_normalized]
        """
        score_normalization = ScoreNormalization(self.sql_manager)

        for p in self.params:
            if p[3]:
                if p[1] is not None:
                    p[1] = score_normalization.get_normalize_score(p[0], p[1])
            else:
                p[1] = score_format(p[1])

        self.sql_manager.save()

        return self.params

    def get_global_score(self):
        """
        To be called after get_normalized_params()
        :return: Return the global score of all criteria
        """
        score = 0
        nb_criteria_implemented = 0

        for p in self.params:
            if p[1] is not None:
                score += p[1]
                nb_criteria_implemented += 1
        return score_format(score / nb_criteria_implemented)
