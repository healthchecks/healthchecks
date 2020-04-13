# Projects and Teams

Use Projects to organize checks in your SITE_NAME account. Your account initially
has a single default project. You can create additional projects and organize
your checks in them as your usage grows.

![An overview of projects](IMG_URL/projects.png)

Checks and integrations are project-scoped: each check and each configured
integration always belongs to a particular project. Checks can be transferred
from one project to another, preserving check's ping address:

![The transfer dialog](IMG_URL/transfer_check.png)

## Team Access

You can grant your colleagues access to a project by inviting them into
the project's team. Each project has its own separate team so you can grant access
selectively. Inviting team members is **more convenient and more
secure** than sharing a password to a single account.

![Team access section](IMG_URL/team_access.png)

The user who originally created the project is listed as **owner**. Any invited users
are listed as **members**. The members can:

* create, edit and remove checks
* create and remove integrations
* rename the project
* view and regenerate project's API keys
* give up their membership
(from their [Account Settings](../../accounts/profile) page)

The members **can not**:

* invite new members into the project
* manage project's billing
* remove the project

## Projects and Check Limits

**Check limit** is the total number of checks your account can have. The specific
limit depends on the account's billing plan.

Account's check limit is shared by all projects owned by your account.
For example, consider a Business account with two projects,
"Project A" and "Project B". If A has 70 checks, then B cannot have more than
30 checks, in order to not exceed business account's total limit of 100.

However, only checks from your own projects count towards your account's
quota. If you get invited to somebody else's project, that does not change
the number of checks you can create in your own projects.

## Projects and Team Size Limits

**Team size** is the number of unique users you can invite in your projects.
The team size limit is also shared by all projects owned by your account.
However, if you invite the same user (using the same email address) into several
projects, it only takes up a single "seat".

## Projects and Monthly Reports

SITE_NAME sends monthly email reports at the
start of each month. The monthly reports list a summary of checks from
**all projects you have access to** (either as the owner or as a member).
