How to build the docs
=====================

From the root directory of the repository, do the following in steps

1. Install docs' dependencies

   .. code-block:: text

       cargo install mdbook --locked

    Or quicker if you have `cargo-binstall` installed:

   .. code-block:: text

       cargo binstall mdbook


2. Build the docs

   .. code-block:: text

       mdbook build

   Or use the following command to see changes rendered in real-time.

   .. code-block:: text

       mdbook serve
