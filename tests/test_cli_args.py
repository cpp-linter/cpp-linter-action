"""Tests related parsing input from CLI arguments."""
from typing import List
from cpp_linter.run import cli_arg_parser


class TestArgs:
    """Grouped tests using a common namespace declaration"""

    class Args:
        """A pseudo namespace declaration. Each attribute is initialized with the
        corresponding CLI arg's default value."""

        verbosity: int = 10
        database: str = ""
        style: str = "llvm"
        tidy_checks: str = (
            "boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,"
            "clang-analyzer-*,cppcoreguidelines-*"
        )
        version: str = ""
        extensions: List[str] = [
            "c",
            "h",
            "C",
            "H",
            "cpp",
            "hpp",
            "cc",
            "hh",
            "c++",
            "h++",
            "cxx",
            "hxx",
        ]
        repo_root: str = "."
        ignore: str = ".github"
        lines_changed_only: int = 0
        files_changed_only: bool = False
        thread_comments: bool = False
        file_annotations: bool = True

    def test_defaults(self):
        """test default values"""
        args = cli_arg_parser.parse_args("")
        expected = self.Args()
        for key in args.__dict__.keys():
            assert args.__dict__[key] == getattr(expected, key)

    def test_verbosity(self):
        """test verbosity option"""
        args = cli_arg_parser.parse_args(["--verbosity=20"])
        assert args.verbosity == 20

    def test_database(self):
        """test database option"""
        args = cli_arg_parser.parse_args(["--database=build"])
        assert args.database == "build"

    def test_style(self):
        """test style option"""
        args = cli_arg_parser.parse_args(["--style=file"])
        assert args.style == "file"

    def test_tidy_checks(self):
        """test tidy-checks option"""
        args = cli_arg_parser.parse_args(["--tidy-checks=-*"])
        assert args.tidy_checks == "-*"

    def test_version(self):
        """test version option"""
        args = cli_arg_parser.parse_args(["--version=14"])
        assert args.version == "14"

    def test_extensions(self):
        """test extensions option"""
        args = cli_arg_parser.parse_args(["--extensions", ".cpp, .h"])
        assert args.extensions == ["cpp", "h"]
        args = cli_arg_parser.parse_args(["--extensions=cxx, .hpp"])
        assert args.extensions == ["cxx", "hpp"]

    def test_repo_root(self):
        """test repo-root option"""
        args = cli_arg_parser.parse_args(["--repo-root=src"])
        assert args.repo_root == "src"

    def test_ignore(self):
        """test ignore option"""
        args = cli_arg_parser.parse_args(["--ignore=!src|"])
        assert args.ignore == "!src|"

    def test_lines_changed_only(self):
        """test lines-changed-only option"""
        args = cli_arg_parser.parse_args(["--lines-changed-only=True"])
        assert args.lines_changed_only == 1
        args = cli_arg_parser.parse_args(["--lines-changed-only=strict"])
        assert args.lines_changed_only == 2

    def test_files_changed_only(self):
        """test files-changed-only option"""
        args = cli_arg_parser.parse_args(["--files-changed-only=True"])
        assert args.files_changed_only is True

    def test_thread_comments(self):
        """test thread-comments option"""
        args = cli_arg_parser.parse_args(["--thread-comments=True"])
        assert args.thread_comments is True

    def test_file_annotations(self):
        """test file-annotations option"""
        args = cli_arg_parser.parse_args(["--file-annotations=False"])
        assert args.file_annotations is False


if __name__ == "__main__":
    test = TestArgs()
    test.test_defaults()
