# Contributing

Thank you for contributing to this project.

This repository uses `develop` as the integration branch. Do not open pull requests against `main` unless a maintainer explicitly asks for it.

## Workflow Overview

1. Clone the repository.
2. Create a new branch from `develop` for the specific feature, fix, or task you are working on.
3. Make and test your changes locally.
4. Sync your branch with the latest `develop` before opening a pull request.
5. Resolve any merge conflicts locally.
6. Open a pull request into `develop`.

## 1. Clone the Repository

```bash
git clone <repository-url>
cd FUK
```

## 2. Create a Branch From `develop`

Always start from the latest `develop` branch:

```bash
git checkout develop
git pull origin develop
```

Create a focused branch for the work you are doing:

```bash
git checkout -b feature/short-description
```

Examples:

```bash
git checkout -b feature/login-page
git checkout -b fix/api-timeout
git checkout -b chore/update-docs
```

Use one branch per task. Do not combine unrelated changes in the same branch.

## 3. Make Your Changes

After creating your branch:

```bash
git status
```

Implement your changes, run any relevant local checks, and review your work before committing.

Commit with a clear message:

```bash
git add .
git commit -m "Add login page validation"
```

## 4. Keep Your Branch Updated With `develop`

Before creating a pull request, make sure your branch includes the latest changes from `develop`.

First, fetch the newest remote updates:

```bash
git fetch origin
```

Then switch to your branch if needed:

```bash
git checkout feature/short-description
```

Merge `develop` into your branch:

```bash
git merge origin/develop
```

If there are no conflicts, continue with your normal flow.

## 5. Resolve Merge Conflicts Before Creating a PR

If Git reports conflicts during the merge, resolve them locally before opening your pull request.

### Step 1: Check Which Files Have Conflicts

```bash
git status
```

Git will show the files that need attention.

### Step 2: Open the Conflicted Files

Look for conflict markers like:

```text
<<<<<<< HEAD
your changes
=======
incoming changes from develop
>>>>>>> origin/develop
```

Edit the file so it contains the correct final version, then remove all conflict markers.

### Step 3: Mark Conflicts as Resolved

After fixing each file:

```bash
git add <file-name>
```

Repeat this for every conflicted file.

### Step 4: Complete the Merge

Once all conflicts are resolved:

```bash
git commit
```

If Git already created the merge commit message, save it as-is or update it if needed.

### Step 5: Verify Everything Still Works

Run the relevant checks for your changes before pushing. At minimum:

```bash
git status
```

Make sure there are no unresolved conflicts and your branch is ready to push.

## 6. Push Your Branch

```bash
git push -u origin feature/short-description
```

## 7. Open a Pull Request

When opening your pull request:

- Set the base branch to `develop`
- Do not target `main`
- Use a clear title and description
- Explain what changed and why
- Mention any testing you performed

## Pull Request Checklist

Before submitting a PR, confirm that:

- Your branch was created from `develop`
- Your work is limited to one specific task
- You merged the latest `develop` into your branch
- All merge conflicts were resolved locally
- Your changes were reviewed locally
- The pull request targets `develop`

## Quick Example

```bash
git clone <repository-url>
cd FUK
git checkout develop
git pull origin develop
git checkout -b feature/add-user-profile

# make changes

git add .
git commit -m "Add user profile page"
git fetch origin
git merge origin/develop

# resolve conflicts if needed

git push -u origin feature/add-user-profile
```
