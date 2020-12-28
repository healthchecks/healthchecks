# Projects and Teams

Use Projects to organize checks in your SITE_NAME account. Your account initially
has a single default project. You can create additional projects and transfer
your checks between them as your usage grows.

![An overview of projects](IMG_URL/projects.png)

Checks and integrations are project-scoped: each check and each configured
integration always belongs to a particular project. Checks can be transferred
between projects. The transfer operation preserves check's ping address:

![The transfer dialog](IMG_URL/transfer_check.png)

## Team Access

You can grant your colleagues access to a project by inviting them into
the project's team. Each project has its separate team so you can grant access
selectively. Inviting team members is **more convenient and more
secure** than sharing a password to a single account.

![Team access section](IMG_URL/team_access.png)

The user who created the project is the **owner**. Any invited users
are **members**. The members can:

* create, edit and remove checks
* create and remove integrations
* rename the project
* view and regenerate project's API keys
* give up their membership
(from their [Account Settings](../../accounts/profile/) page)

The members **can not**:

* invite new members into the project
* manage project's billing
* remove the project

## Read-only Access

When inviting a team member, you can mark their membership as read-only:

![The Access Level parameter in the Invite form](IMG_URL/invite_member.png)

Read-only members can:

* view checks, including check details and ping logs
* view integrations
* give up their membership

Read-only members can not modify checks, integrations, or project settings.
They also cannot access the project's API keys as that would effectively give them
read-write access through API.

## Projects and Check Limits

**Check Limit** is the total number of checks your account can have. The specific
limit depends on the account's billing plan. When you reach the Check Limit
you will not be able to create new checks.

All projects owned by your account shares your account's Check Limit.
For example, consider a Business account with two projects,
"Project A" and "Project B." If A has 70 checks, then B cannot have more than
30 checks in order to not exceed the Business account's total limit of 100.

However, only checks from your own projects count towards your account's
quota. If you get invited to somebody else's project, that does not change
the number of checks you can create in your projects.

## Projects and Team Size Limits

**Team Size** is the number of *unique* users you can invite to your projects.
Same as with Check Limit, all projects share your account's Team Size limit.
However, if you invite the same user (using the same email address) into multiple
projects, it only takes up a single seat.

## Projects and Monthly Reports

SITE_NAME sends monthly email reports at the start of each month. The monthly reports
list a summary of checks from **all your projects**. It contains status summaries for
both the projects you own and the projects you are a member of.
