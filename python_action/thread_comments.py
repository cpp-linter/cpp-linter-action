"""A module to house the various functions for traversing/adjusting comments"""
import os
import requests
import json
from . import Globals, GlobalParser, logger, API_HEADERS, GITHUB_SHA, log_response_msg


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


def list_diff_comments():
    """Aggregate list of comments for use in the event's diff. This function assumes
    that the CLI option `--diff-only` is set to True.

    Returns:
        A list of comments (each element as json content).
    """
    results = []
    for index, fixit in enumerate(GlobalParser.tidy_advice):
        for diag in fixit.diagnostics:
            # base body of comment
            body = "<!-- cpp linter action -->\n**" + diag.name + "**\n>" + diag.message

            # assemble a suggestion (only if for a single line)
            fix_lines = []  # a list of line numbers for the suggested fixes
            suggestion = "\n```suggestion\n"
            is_multiline_fix = False
            # get original code
            filename = Globals.FILES[index]["filename"].replace("/", os.sep)
            if not os.path.exists(filename):
                # the file had to be downloaded (no git checkout).
                # thus use only the filename (without the path to the file)
                filename = os.path.split(filename)[1]
            lines = []  # the list of lines in a file
            line = ""  # the line that concerns the fix/comment
            with open(filename) as temp:
                lines = temp.readlines()

            for i, fix in enumerate(diag.replacements):
                line = lines[fix.line - 1]
                if not fix_lines:
                    fix_lines.append(fix.line)
                elif fix.line not in fix_lines:
                    is_multiline_fix = True
                    break
                if i:  # if this isn't the first fix for the same line
                    last_fix = diag.replacements[i - 1]
                    suggestion += line[
                        last_fix.cols + last_fix.null_len - 1 : fix.cols - 1
                    ] + fix.text.decode()
                else:
                    suggestion += line[: fix.cols - 1] + fix.text.decode()
            if not is_multiline_fix and diag.replacements:
                last_fix = diag.replacements[len(diag.replacements) - 1]
                suggestion += line[last_fix.cols + last_fix.null_len - 1: -1] + "\n```"
                body += suggestion

            results.append(
                {
                    "body": body,
                    "commit_id": GITHUB_SHA,
                    "line": diag.line,
                    "path": fixit.filename,
                    "side": "RIGHT",
                }
            )
    return results


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
    review_id = find_review(json.loads(Globals.response_buffer.text), user_id)
    if review_id is None:  # create a PR review
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
        if Globals.response_buffer.status_code != 200:
            log_response_msg()
            raise RuntimeError("could not create a review for commemts")
        reviews = json.loads(Globals.response_buffer.text)
        reviews.reverse()  # traverse the list in reverse
        review_id = find_review(reviews, user_id)
    return review_id


def find_review(reviews: dict, user_id: int):
    """Find a review created by a certain user ID."""
    review_id = None
    for review in reviews:
        if int(review["user"]["id"]) == user_id and review["body"].startswith(
            "<!-- cpp linter action -->"
        ):
            review_id = int(review["id"])
            break  # there will only be 1 review from this action, so break when found

    logger.info(f"   review_id: {review_id}")
    return review_id
