# coding=utf-8

import readability
import numpy as np


# ---------- Taux d'accord ----------

# metrique de calcul du taux d'accord
def nominal_metric(a, b):
    return a != b


# metrique de calcul du taux d'accord
def interval_metric(a, b):
    return (a - b) ** 2


# construit les catégories pour le calcul d'alpha
def calcul_tab_categorie(mediane):
    pas = 20
    tab = []
    # calcul des categories en fonction de la moyenne
    mediane_initiale = mediane
    tab.insert(0, [mediane - pas / 2, mediane + pas / 2])
    while mediane - pas / 2 > 0:
        mediane -= pas
        tab.insert(0, [mediane - pas / 2, mediane + pas / 2])
    mediane_initiale += pas
    while mediane_initiale - pas / 2 < 100:
        tab.append([mediane_initiale - pas / 2, mediane_initiale + pas / 2])
        mediane_initiale += pas

    print("tab categories :", tab)
    return tab


# calcule et renvoie le coef alpha
def krippendorff_alpha(data, metric, force_vecmath=False, convert_items=float):

    # set of constants identifying missing values
    maskitems = []

    # convert input data to a dict of items
    units = {}
    for d in data:
        try:
            # try if d behaves as a dict
            diter = d.items()
        except AttributeError:
            # sequence assumed for d
            diter = enumerate(d)

        for it, g in diter:
            if g not in maskitems:
                try:
                    its = units[it]
                except KeyError:
                    its = []
                    units[it] = its
                its.append(convert_items(g))

    units = dict((it, d) for it, d in units.items() if len(d) > 1)  # units with pairable values
    n = sum(len(pv) for pv in units.values())  # number of pairable values

    if n == 0:
        raise ValueError("No items to compare.")

    np_metric = (np is not None) and ((metric in (interval_metric, nominal_metric)) or force_vecmath)

    do = 0.
    for grades in units.values():
        if np_metric:
            gr = np.asarray(grades)
            du = sum(np.sum(metric(gr, gri)) for gri in gr)
        else:
            du = sum(metric(gi, gj) for gi in grades for gj in grades)
        do += du / float(len(grades) - 1)
    do /= float(n)

    if do == 0:
        return 1.

    de = 0.
    for g1 in units.values():
        if np_metric:
            d1 = np.asarray(g1)
            for g2 in units.values():
                de += sum(np.sum(metric(d1, gj)) for gj in g2)
        else:
            for g2 in units.values():
                de += sum(metric(gi, gj) for gi in g1 for gj in g2)
    de /= float(n * (n - 1))

    return 1. - do / de if (do and de) else 1.


# calcule et renvoie de taux d'accord après avoir construit les données d'entrées
def calcul_kirppendorf(tab_normalized_score, mediane):
    tab = calcul_tab_categorie(mediane)
    n = len(tab_normalized_score)
    m = len(tab)

    data = []
    for i in range(n):
        value = tab_normalized_score[i]
        for j in range(m):
            code = ["0 "] * m
            if value <= tab[j][1] and value >= tab[j][0]:
                if j - 1 >= 0:
                    code[j - 1] = "1 "
                code[j] = "1 "
                if j + 1 < m:
                    code[j + 1] = "1 "
                data.append(" ".join(code))
    print(data)
    array = [d.split() for d in data]

    return krippendorff_alpha(array, interval_metric)


# ---------- Mediane des résultats de readability ----------

# renvoie le score normalisé du score en paramètre
def score_grade(read_grades_tab_i, vmin, vmax):
    val = read_grades_tab_i[1]

    if val < vmin:
        val = 0
    elif val > vmax:
        val = 100
    else:
        # Flesch est la seule valeur non inversée par rapport à notre échelle : 0 = difficile, 100 = facile
        if read_grades_tab_i[0] == "FleschReadingEase":
            val = val * 100 / vmax
        else:
            val = 100 - val * 100 / vmax

    return val


# calcule et renvoie la mediane et le tableau de score normalisé
def calcul_mediane(read_grades_tab, sentence_info_tab):

    tab_score = []
    for i in range(len(read_grades_tab) - 1):
        if read_grades_tab[i][0] == "Kincaid" or read_grades_tab[i][0] == "ARI":
            tab_score.append(score_grade(read_grades_tab[i], 5, 20))
        elif read_grades_tab[i][0] == "FleschReadingEase":
            tab_score.append(score_grade(read_grades_tab[i], 0, 100))
        elif read_grades_tab[i][0] == "LIX":
            tab_score.append(score_grade(read_grades_tab[i], 0, 100))
        elif read_grades_tab[i][0] == "GunningFogIndex" or read_grades_tab[i][0] == "Coleman-Liau":
            if sentence_info_tab[7][1] >= 100:
                tab_score.append(score_grade(read_grades_tab[i], 5, 20))
            else:
                print("La formule de", read_grades_tab[i][0],
                      "ne peut pas être utilisée car il y a moins de 100 mots (", sentence_info_tab[7][1], ").")
        elif read_grades_tab[i][0] == "SMOGIndex":
            if sentence_info_tab[9][1] >= 30:
                tab_score.append(score_grade(read_grades_tab[i], 5, 20))
            else:
                print("La formule de", read_grades_tab[i][0],
                      "ne peut pas être utilisée car il y a moins de 30 phrases (", sentence_info_tab[9][1], ").")
    tab_score.sort()
    # print(tab_score)
    n = len(tab_score)
    if n % 2 == 0:
        mediane = (tab_score[n // 2] + tab_score[(n + 1) // 2]) // 2
    else:
        mediane = tab_score[(n + 1) // 2]

    return [mediane, tab_score]


# calcule et renvoie la mediane et le taux d'accord
# fonction mère
def calcul_readability(results):
    read_grades_tab = []
    sentence_info_tab = []

    for niveau1, niveau2 in results.items():
        for titre, valeur in niveau2.items():
            if niveau1 == "readability grades":
                read_grades_tab.append([titre, valeur])
            elif niveau1 == "sentence info":
                sentence_info_tab.append([titre, valeur])

    [mediane, tab_normalized_score] = calcul_mediane(read_grades_tab, sentence_info_tab)
    taux_accord = calcul_kirppendorf(tab_normalized_score, mediane)

    return mediane, taux_accord


# ---------- Classe Readability ----------

# renvoie le taux de readability d'un texte
# plus le taux est élevé plus le texte est difficile à lire
class Readability:

    def __init__(self, text):
        self.text = text

    def get_score(text):
        print("------------READABILITY -------------------------------------")
        results = readability.getmeasures(text, lang='en')
        mediane, taux_accord = calcul_readability(results)
        print(mediane, "(", taux_accord, ")\n-------------------------------------------------------------")
        return mediane, taux_accord