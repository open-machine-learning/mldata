"""
Template tag to show stars in ratings

@var IMG_TEMPLATE: template to use for including the star image
@type IMG_TEMPLATE: string
@var PATH_TO_WHOLE_STAR: URL path to whole star
@type PATH_TO_WHOLE_STAR: string
@var PATH_TO_THREE_QUARTER_STAR: URL path to 3/4 star
@type PATH_TO_THREE_QUARTER_STAR: string
@var PATH_TO_HALF_STAR: URL path to halfe star
@type PATH_TO_HALF_STAR: string
@var PATH_TO_QUARTER_STAR: URL path to quarter star
@type PATH_TO_QUARTER_STAR: string
@var PATH_TO_BLANK_STAR: URL path to blank star
@type PATH_TO_BLANK_STAR: string
"""

import math
from django.template import Library, Node, TemplateSyntaxError, VariableDoesNotExist, resolve_variable
from django.conf import settings

register = Library()

IMG_TEMPLATE = '<img src="%s" alt="%s"/>'
PATH_TO_WHOLE_STAR = IMG_TEMPLATE % (settings.MEDIA_URL + 'images/stars/star.png', "Whole Star")
PATH_TO_THREE_QUARTER_STAR = IMG_TEMPLATE % (settings.MEDIA_URL + 'images/stars/three-quarter.png', "3/4 Star")
PATH_TO_HALF_STAR = IMG_TEMPLATE % (settings.MEDIA_URL + 'images/stars/half.png', "1/2 Star")
PATH_TO_QUARTER_STAR = IMG_TEMPLATE % (settings.MEDIA_URL + 'images/stars/quarter.png', "1/4 Star")
PATH_TO_BLANK_STAR = IMG_TEMPLATE % (settings.MEDIA_URL + 'images/stars/blank.png', "Empty Star")

class ShowStarsNode(Node):
    """Default rounding is to the whole unit.

    @ivar context_var: context variable
    @type context_var: unknown
    @ivar total_stars: total number of stars
    @type total_stars: integer
    @ivar round_to: round to
    @type round_to: string
    """

    def __init__(self, context_var, total_stars, round_to):
        """Initialize node."""
        self.context_var = context_var
        self.total_stars = int(total_stars)
        self.round_to = round_to.lower()

    def render(self, context):
        """Render node.

        @param context: context to render in.
        @type context: unknown
        @return rendered stars (or blank on failure)
        @rtype: string
        """
        try:
            stars = resolve_variable(self.context_var, context)
        except VariableDoesNotExist:
            return ''

        if self.round_to == "half":
            stars = round(stars*2)/2
        elif self.round_to == "quarter":
            stars = round(stars*4)/4
        else:
            stars = round(stars)

        fraction, integer = math.modf(stars)
        integer = int(integer)
        output = []

        for whole_star in range(integer):
            output.append(PATH_TO_WHOLE_STAR)
        if self.round_to == 'half' and fraction == .5:
            output.append(PATH_TO_HALF_STAR)
        elif self.round_to == 'quarter':
            if fraction == .25:
                output.append(PATH_TO_QUARTER_STAR)
            elif fraction == .5:
                output.append(PATH_TO_HALF_STAR)
            elif fraction == .75:
                output.append(PATH_TO_THREE_QUARTER_STAR)

        if fraction:
            integer += 1

        blanks = int(self.total_stars - integer)
        for blank_star in range(blanks):
            output.append(PATH_TO_BLANK_STAR)

        return "".join(output)

def do_show_stars(parser, token):
    """Show stars context_var of 5 round to half.

    @param parser: parser
    @type parser: unknown
    @param token: arguments
    @type token: unknown
    """
    args = token.contents.split()
    if len(args) != 7:
        raise TemplateSyntaxError('%s tag requires exactly six arguments' % args[0])
    if args[2] != 'of':
        raise TemplateSyntaxError("second argument to '%s' tag must be 'of'" % args[0])
    if args[4] != 'round':
        raise TemplateSyntaxError("fourth argument to '%s' tag must be 'round'" % args[0])
    if args[5] != 'to':
        raise TemplateSyntaxError("fourth argument to '%s' tag must be 'to'" % args[0])
    return ShowStarsNode(args[1], args[3], args[6])
register.tag('show_stars', do_show_stars)
