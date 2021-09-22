"""A module to house the various functions for traversing/adjusting comments"""
import enum
import requests
import json
from . import Globals, GlobalParser, logger, API_HEADERS


def remove_bot_comments(comments_url: str, user_id: int):
    """Traverse the list of comments made by a specific user
    and remove all.

    Args:
        comments_url: The URL used to fetch the comments.
        user_id: The user's account id number.
    Returns:
        The number of comments for the given URL's thread.
    """
    logger.info(f"comments_url: {comments_url}")
    Globals.response_buffer = requests.get(comments_url)
    comments = Globals.response_buffer.json()
    for i, comment in enumerate(comments):
        # only serach for comments from the user's ID and
        # whose comment body begins with a specific html comment
        if (
            int(comment["user"]["id"]) == user_id
            # the specific html comment is our action's name
            and comment["body"].startswith("<!-- cpp linter action -->")
        ):
            # remove other outdated comments but don't remove the last comment
            Globals.response_buffer = requests.delete(
                comment["url"],
                headers=API_HEADERS,
            )
            logger.info(
                f"Got {Globals.response_buffer.status_code} from DELETE "
                f"{comment['url'][comment['url'].find('.com') + 4 :]}"
            )
            del comments[i]
        logger.debug(
            f'comment id {comment["id"]} from user {comment["user"]["login"]}'
            f' ({comment["user"]["id"]})'
        )
    with open("comments.json", "w", encoding="utf-8") as json_comments:
        json.dump(comments, json_comments, indent=4)


def get_review_id(reviews_url: str, user_id: int):
    """Dismiss all stale reviews (only the ones made by our bot).

    Args:
        reviews_url: The URL used to fetch the review comments.
        user_id: The user's account id number.
    Returns:
        The ID number of the review created by the action's generic bot.
    """
    logger.info(f"  review_url: {reviews_url}")
    Globals.response_buffer = requests.get(reviews_url)
    review_id = None
    reviews = Globals.response_buffer.json()
    if not reviews:  # create a PR review
        Globals.response_buffer = requests.post(
            reviews_url,
            headers=API_HEADERS,
            data=json.dumps(
                {
                    "body": "<!-- cpp linter action -->\n"
                    "CPP Linter Action found no problems",
                    "event": "COMMENTED",
                }
            ),
        )
        logger.info(
            "Got %d from POSTing new(/temp) PR review",
            Globals.response_buffer.status_code,
        )
        Globals.response_buffer = requests.get(reviews_url)
        reviews = Globals.response_buffer.json()
        reviews.reverse()  # traverse the list in reverse

    for review in reviews:
        if int(review["user"]["id"]) == user_id and review["body"].startswith(
            "<!-- cpp linter action -->"
        ):
            review_id = int(review["id"])
            break  # there will only be 1 review from this action, so break when found

    logger.info(f"   review_id: {review_id}")
    return review_id


def list_diff_comments():
    """Aggregate list of comments for use in the event's diff. This function assumes
    that the CLI option `--diff-only` is set to True.

    Returns:
        A list of comments (each element as json content).
    """
    results = []
    for index, fixit in enumerate(GlobalParser.tidy_advice):
        for diag in fixit.diagnostics:
            results.append(
                {
                    "body": "<!-- cpp linter action -->\n" + diag.name,
                    "position": Globals.FILES[index]["diff_line_map"][diag.line],
                    "path": fixit.filename,
                    "side": "RIGHT",
                }
            )
    return results

def outdate_review_comment(url: str, review_id: str, review_author: str):
    """Edit an outdated a comment.

    Args:
        url: The URL to the comment to be edited.
    """
    Globals.response_buffer = requests.put(
        url,
        headers=API_HEADERS,
        data=json.dumps({"body": "This outdated comment has been edited."}),
    )
    logger.info(
        "Got {} from editing review comment {} by {}".format(
            Globals.response_buffer.status_code,
            review_id,
            review_author,
        )
    )
