from numpy import *

class ClassificationErrorRate:
    """ Classification evaluation using Error Rate """

    def run(self, matrix1, matrix2):
        """ This function will calculate the error rate 
        between two matrices"""

        prediction = 0
        correct_class = 0
        errors = 0
        index = 0
        size = len(matrix1)

        for index in range(size):
            correct_class = matrix1[index]
            prediction = matrix2[index]

            if (prediction != correct_class):
                errors = errors + 1
        return 100*errors/size



class RegressionMAE:
    """ Regression evaluation using Mean Absolute Error """

    def run(self, matrix1, matrix2):
        """ This function will calculate MAE between two matrices"""

        next1 = ' '
        next2 = ' '
        prediction = 0.0
        correct_value = 0.0
        mae = 0.0
        errorsum = 0.0
        index = 0
        size = len(matrix1)

        for index in range(size):
            correct_value = matrix1[index]
            prediction = matrix2[index]
            errorsum = errorsum + abs(correct_value-prediction)
        return errorsum/size



class RegressionRMSE:
    """ Regression evaluation using Root Mean Squared Error """

    def run(self, matrix1, matrix2):
        """ This function will calculate RMSE between two matrices"""

        next1 = ' '
        next2 = ' '
        prediction = 0.0
        correct_value = 0.0
        errorsum = 0.0
        index = 0
        size = len(matrix1)

        for index in range(size):
            correct_value = matrix1[index]
            prediction = matrix2[index]
            errorsum = errorsum + (correct_value-prediction)**2
        return sqrt(errorsum/size)
