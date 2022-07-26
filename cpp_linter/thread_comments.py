"""A module to house the various functions for traversing/adjusting comments"""
import os
from typing import Union, cast, List, Optional
import json
import requests
from . import Globals, GlobalParser, logger, API_HEADERS, GITHUB_SHA, log_response_msg


def remove_bot_comments(comments_url: str, user_id: int):
    """Traverse the list of comments made by a specific user
    and remove all.

    Args:
        comments_url: The URL used to fetch the comments.
        user_id: The user's account id number.
    """
    logger.info("comments_url: %s", comments_url)
    Globals.response_buffer = requests.get(comments_url)
    if not log_response_msg():
        return  # error getting comments for the thread; stop here
    comments = Globals.response_buffer.json()
    for comment in comments:
        # only search for comments from the user's ID and
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
                "Got %d from DELETE %s",
                Globals.response_buffer.status_code,
                comment["url"][comment["url"].find(".com") + 4 :],
            )
            log_response_msg()
        logger.debug(
            "comment id %d from user %s (%d)",
            comment["id"],
            comment["user"]["login"],
            comment["user"]["id"],
        )
    with open("comments.json", "w", encoding="utf-8") as json_comments:
        json.dump(comments, json_comments, indent=4)


def aggregate_tidy_advice() -> list:
    """Aggregate a list of json contents representing advice from clang-tidy
    suggestions."""
    results = []
    for index, fixit in enumerate(GlobalParser.tidy_advice):
        for diag in fixit.diagnostics:
            # base body of comment
            body = "<!-- cpp linter action -->\n## :speech_balloon: Clang-tidy\n**"
            body += diag.name + "**\n>" + diag.message

            # get original code
            filename = cast(str, Globals.FILES[index]["filename"]).replace("/", os.sep)
            if not os.path.exists(filename):
                # the file had to be downloaded (no git checkout).
                # thus use only the filename (without the path to the file)
                filename = os.path.split(filename)[1]
            lines = []  # the list of lines in a file
            with open(filename, encoding="utf-8") as temp:
                lines = temp.readlines()

            # aggregate clang-tidy advice
            suggestion = "\n```suggestion\n"
            is_multiline_fix = False
            fix_lines: List[int] = []  # a list of line numbers for the suggested fixes
            line = ""  # the line that concerns the fix/comment
            for i, tidy_fix in enumerate(diag.replacements):
                line = lines[tidy_fix.line - 1]
                if not fix_lines:
                    fix_lines.append(tidy_fix.line)
                elif tidy_fix.line not in fix_lines:
                    is_multiline_fix = True
                    break
                if i:  # if this isn't the first tidy_fix for the same line
                    last_fix = diag.replacements[i - 1]
                    suggestion += (
                        line[last_fix.cols + last_fix.null_len - 1 : tidy_fix.cols - 1]
                        + tidy_fix.text.decode()
                    )
                else:
                    suggestion += line[: tidy_fix.cols - 1] + tidy_fix.text.decode()
            if not is_multiline_fix and diag.replacements:
                # complete suggestion with original src code and closing md fence
                last_fix = diag.replacements[len(diag.replacements) - 1]
                suggestion += line[last_fix.cols + last_fix.null_len - 1 : -1] + "\n```"
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


def aggregate_format_advice() -> list:
    """Aggregate a list of json contents representing advice from clang-format
    suggestions."""
    results = []
    for index, fmt_advice in enumerate(GlobalParser.format_advice):

        # get original code
        filename = cast(str, Globals.FILES[index]["filename"]).replace("/", os.sep)
        if not os.path.exists(filename):
            # the file had to be downloaded (no git checkout).
            # thus use only the filename (without the path to the file)
            filename = os.path.split(filename)[1]
        lines = []  # the list of lines from the src file
        with open(filename, encoding="utf-8") as temp:
            lines = temp.readlines()

        # aggregate clang-format suggestion
        line = ""  # the line that concerns the fix
        for fixed_line in fmt_advice.replaced_lines:
            # clang-format can include advice that starts/ends outside the diff's domain
            in_range = False
            ranges: List[List[int]] = Globals.FILES[index]["line_filter"]["lines"]  # type: ignore
            for scope in ranges:
                if fixed_line.line in range(scope[0], scope[1] + 1):
                    in_range = True
            if not in_range:
                continue  # line is out of scope for diff, so skip this fix

            # assemble the suggestion
            body = "## :scroll: clang-format advice\n```suggestion\n"
            line = lines[fixed_line.line - 1]
            # logger.debug("%d >>> %s", fixed_line.line, line[:-1])
            for fix_index, line_fix in enumerate(fixed_line.replacements):
                # logger.debug(
                #     "%s >>> %s", repr(line_fix), line_fix.text.encode("utf-8")
                # )
                if fix_index:
                    last_fix = fixed_line.replacements[fix_index - 1]
                    body += line[
                        last_fix.cols + last_fix.null_len - 1 : line_fix.cols - 1
                    ]
                    body += line_fix.text
                else:
                    body += line[: line_fix.cols - 1] + line_fix.text
            # complete suggestion with original src code and closing md fence
            last_fix = fixed_line.replacements[-1]
            body += line[last_fix.cols + last_fix.null_len - 1 : -1] + "\n```"
            # logger.debug("body <<< %s", body)

            # create a suggestion from clang-format advice
            results.append(
                {
                    "body": body,
                    "commit_id": GITHUB_SHA,
                    "line": fixed_line.line,
                    "path": fmt_advice.filename,
                    "side": "RIGHT",
                }
            )
    return results


def concatenate_comments(tidy_advice: list, format_advice: list) -> list:
    """Concatenate comments made to the same line of the same file."""
    # traverse comments from clang-format
    for index, comment_body in enumerate(format_advice):
        # check for comments from clang-tidy on the same line
        comment_index = None
        for i, payload in enumerate(tidy_advice):
            if (
                payload["line"] == comment_body["line"]
                and payload["path"] == comment_body["path"]
            ):
                comment_index = i  # mark this comment for concatenation
                break
        if comment_index is not None:
            # append clang-format advice to clang-tidy output/suggestion
            tidy_advice[comment_index]["body"] += "\n" + comment_body["body"]
            del format_advice[index]  # remove duplicate comment
    return tidy_advice + format_advice


def list_diff_comments() -> list:
    """Aggregate list of comments for use in the event's diff. This function assumes
    that the CLI option `--diff-only` is set to True.

    Returns:
        A list of comments (each element as json content).
    """
    tidy_advice = aggregate_tidy_advice()
    format_advice = aggregate_format_advice()
    results = concatenate_comments(tidy_advice, format_advice)
    return results


def get_review_id(reviews_url: str, user_id: int) -> Optional[int]:
    """Dismiss all stale reviews (only the ones made by our bot).

    Args:
        reviews_url: The URL used to fetch the review comments.
        user_id: The user's account id number.
    Returns:
        The ID number of the review created by the action's generic bot.
    """
    logger.info("  review_url: %s", reviews_url)
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
        if Globals.response_buffer.status_code != 200 and log_response_msg():
            raise RuntimeError("could not create a review for comments")
        reviews = json.loads(Globals.response_buffer.text)
        reviews.reverse()  # traverse the list in reverse
        review_id = find_review(reviews, user_id)
    return review_id


def find_review(reviews: dict, user_id: int) -> Union[int, None]:
    """Find a review created by a certain user ID.

    Args:
        reviews: the JSON object fetched via GIT REST API.
        user_id: The user account's ID number

    Returns:
        An ID that corresponds to the specified `user_id`.
    """
    review_id = None
    for review in reviews:
        if int(review["user"]["id"]) == user_id and review["body"].startswith(
            "<!-- cpp linter action -->"
        ):
            review_id = int(review["id"])
            break  # there will only be 1 review from this action, so break when found

    logger.info("   review_id: %d", review_id)
    return review_id
