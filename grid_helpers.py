import base64
from functools import reduce
from urllib.parse import unquote_plus

from py4web import request, Field, response
from py4web.utils.form import Form, FormStyleBulma

from yatl.helpers import (
    TAG,
)

BUTTON = TAG.button


class GridSearchQuery:
    def __init__(self, name, query, requires=None, datatype="str", default=None):
        self.name = name
        self.query = query
        self.requires = requires
        self.datatype = datatype
        self.default = default

        self.field_name = name.replace(" ", "_").lower()


class GridSearch:
    def __init__(
        self, search_queries, queries=None, target_element=None, formname="search_form"
    ):
        self.search_queries = search_queries
        self.queries = queries

        field_names = []
        field_requires = dict()
        field_datatype = dict()
        field_default = dict()
        for field in self.search_queries:
            field_name = "sq_" + field.name.replace(" ", "_").replace("/", "_").lower()
            field_names.append(field_name)
            if field.requires and field.requires != "":
                field_requires[field_name] = field.requires
            if field.datatype and field.datatype.lower() == "boolean":
                field_datatype[field_name] = "boolean"
            elif field.datatype and field.datatype.lower() == "date":
                field_datatype[field_name] = "date"
            elif field.datatype and field.datatype.lower() == "datetime":
                field_datatype[field_name] = "datetime"
            if field.default:
                field_default[field_name] = field.default

        field_values = dict()
        for field in field_names:
            if field in request.forms:
                field_values[field] = unquote_plus(request.forms.get(field))
            elif field in request.query:
                field_values[field] = unquote_plus(request.query[field])

        form_fields = []
        for field in field_names:
            label = field.replace("sq_", "").replace("_", " ").title()
            placeholder = field.replace("sq_", "").replace("_", " ").capitalize()
            if field in field_datatype:
                datatype = field_datatype[field]
            else:
                datatype = "str"

            if datatype == "boolean":
                if field_values.get(field):
                    default = field_values.get(field)
                else:
                    default = field_default.get(field)
                if default:
                    form_fields.append(
                        Field(
                            field,
                            type=field_datatype[field],
                            label=label,
                            _title=placeholder,
                            default=True,
                        )
                    )
                else:
                    form_fields.append(
                        Field(
                            field,
                            type=field_datatype[field],
                            label=label,
                            _title=placeholder,
                        )
                    )
            else:
                form_fields.append(
                    Field(
                        field,
                        type=field_datatype.get(field, "str"),
                        length=50,
                        _placeholder=placeholder,
                        label=label,
                        requires=field_requires.get(field),
                        default=field_values.get(field, field_default.get(field)),
                        _title=placeholder,
                        _class=field_datatype.get(field, "input"),
                    )
                )

        if target_element:
            attrs = {
                "_hx-post": request.url,
                "_hx-target": target_element,
                "_hx-swap": "innerHTML",
                "_method": "GET",
            }
        else:
            attrs = {"_method": "GET"}

        self.search_form = Form(
            form_fields,
            keep_values=True,
            formstyle=FormStyleBulma,
            form_name=formname,
            **attrs,
        )

        if self.search_form.accepted:
            for field in field_names:
                if (
                    field in field_datatype
                    and field_datatype[field].lower() == "boolean"
                ):
                    if field in self.search_form.vars:
                        field_values[field] = self.search_form.vars[field]
                    else:
                        field_values[field] = False
                else:
                    field_values[field] = self.search_form.vars[field]

        if not self.queries:
            self.queries = []

        for sq in self.search_queries:
            field_name = "sq_" + sq.name.replace(" ", "_").replace("/", "_").lower()
            if field_name in field_values and field_values[field_name]:
                self.queries.append(sq.query(field_values[field_name]))
            elif field_name in field_default and field_default[field_name]:
                self.queries.append(sq.query(field_default[field_name]))

        self.query = reduce(lambda a, b: (a & b), self.queries)


def apply_htmx_attrs(grid, target):
    myattrs = {"_hx-post": request.url, "_hx-target": target, "_hx-swap": "innerHTML"}

    grid.attributes_plugin["form"] = lambda attrs: attrs.update(myattrs)
    grid.attributes_plugin["link"] = lambda attrs: attrs.update(myattrs)
    grid.attributes_plugin["search_form"] = lambda attrs: attrs.update(myattrs)
    grid.attributes_plugin["button_sort_up"] = lambda attrs: attrs.update(myattrs)
    grid.attributes_plugin["button_sort_down"] = lambda attrs: attrs.update(myattrs)
    grid.attributes_plugin["button_delete"] = lambda attrs: attrs.update(myattrs)
    grid.attributes_plugin["button_page_number"] = lambda attrs: attrs.update(myattrs)


def get_referrer(r, default):
    referrer = r.query.get("_referrer")
    url = default
    if referrer:
        url = base64.b16decode(referrer.encode("utf8")).decode("utf8")

    return url


def enable_htmx_grid(htmx_grid, target, default_referrer, after_swap=None):
    """
    Turn this grid into an htmx-capable grid.
    Add the Cancel button
    Call process on the grid (grid must be instantiated with auto_process=False)

    Parameters
    ----------
    htmx_grid: the grid to update
    target: htmx target element
    default_referrer: default URL for the Cancel button
    after_swap: set the javascript function to call after the dom swap is complete - this is to trigger other actions
                after the swap

    Returns
    -------

    """
    attrs = {
        "_hx-get": get_referrer(
            request,
            default=default_referrer,
        ),
        "_class": "button is-default",
    }
    htmx_grid.param.new_sidecar = BUTTON("Cancel", **attrs)
    htmx_grid.param.edit_sidecar = BUTTON("Cancel", **attrs)

    if after_swap:
        if htmx_grid.mode.lower() == "select":
            response.headers["HX-Trigger-After-Swap"] = after_swap

    htmx_grid.process()
