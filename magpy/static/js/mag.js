/*global window, document, localStorage, XMLHttpRequest, Element,
  ActiveXObject, SITE_DOMAIN:true, APP_NAME:true*/
/*jslint nomen: true*/

/**

   SITE_DOMAIN should be set before Raven is included in an HTML document,
   either through a Javascript file or in the HEAD of the HTML document:

   <script type="text/javascript">
   var SITE_DOMAIN = "newvmr.local";
   </script>
   <script type="text/javascript" src="/static/frontend/js/raven.js"></script>

*/

if (typeof SITE_DOMAIN === 'undefined') {
    SITE_DOMAIN = 'localhost';
}

if (typeof APP_NAME === 'undefined') {
    APP_NAME = window.location.pathname.split('/')[1];
}

if (typeof LOCAL_DB_NAME === 'undefined') {
    LOCAL_DB_NAME = 'mag';
}

/** Array.indexOf for IE before IE9 */
if (!Array.prototype.indexOf) {
    Array.prototype.indexOf = function (obj, fromIndex) {
        "use strict";
        var i, j;
        if (fromIndex === null) {
            fromIndex = 0;
        } else if (fromIndex < 0) {
            fromIndex = Math.max(0, this.length + fromIndex);
        }
        for (i = fromIndex, j = this.length; i < j; i += 1) {
            if (this[i] === obj) {
                return i;
            }
        }
        return -1;
    };
}

/** Array.map for IE before IE9 */
// Production steps of ECMA-262, Edition 5, 15.4.4.19
// Reference: http://es5.github.com/#x15.4.4.19
if (!Array.prototype.map) {
    Array.prototype.map = function (callback, thisArg) {
        "use strict";
        var T, A, k, O, len, kValue, mappedValue;
        if (this === null) {
            throw new TypeError(" this is null or not defined");
        }

        // 1. Let O be the result of calling ToObject passing
        // the |this| value as the argument.
        O = Object(this);

        // 2. Let lenValue be the result of calling the Get internal
        // method of O with the argument "length".
        // 3. Let len be ToUint32(lenValue).
        /*jslint bitwise: true*/
        len = O.length >>> 0;
        /*jslint bitwise: false*/

        // 4. If IsCallable(callback) is false, throw a TypeError exception.
        // See: http://es5.github.com/#x9.11
        if ({}.toString.call(callback) !== "[object Function]") {
            throw new TypeError(callback + " is not a function");
        }

        // 5. If thisArg was supplied, let T be thisArg; else let T be undefined.
        if (thisArg) {
            T = thisArg;
        }

        // 6. Let A be a new array created as if by the expression
        // new Array(len) where Array is
        // the standard built-in constructor with that name and
        // len is the value of len.
        A = new Array(len);

        // 7. Let k be 0
        k = 0;

        // 8. Repeat, while k < len
        while (k < len) {

            // a. Let Pk be ToString(k).
            //   This is implicit for LHS operands of the in operator
            // b. Let kPresent be the result of calling the
            // HasProperty internal method of O with argument Pk.
            //   This step can be combined with c
            // c. If kPresent is true, then
            if (k in O) {

                // i. Let kValue be the result of calling the
                // Get internal method of O with argument Pk.
                kValue = O[k];

                // ii. Let mappedValue be the result of calling the
                // Call internal method of callback
                // with T as the this value and argument list containing
                // kValue, k, and O.
                mappedValue = callback.call(T, kValue, k, O);

                // iii. Call the DefineOwnProperty internal method of A
                // with arguments
                // Pk, Property Descriptor {Value: mappedValue,
                // Writable: true, Enumerable: true, Configurable: true},
                // and false.

                // In browsers that support Object.defineProperty,
                // use the following:
                // Object.defineProperty(A, Pk, { value: mappedValue,
                // writable: true, enumerable: true, configurable: true });

                // For best browser support, use the following:
                A[k] = mappedValue;
            }
            // d. Increase k by 1.
            k += 1;
        }

        // 9. return A
        return A;
    };
}

/** MAGPY is a REST/JSON based storage system
    aimed particularly at textual data, used by ITSEE's projects. */
var MAG = (function () {
    "use strict";
    return {
        // body of module here
        get_version: function () {
            return "0.2";
        },

        _EVENT_STORE: {},

        /** Higher-order functions for functional programming */
        FUNCTOOLS: (function () {
            return {
                /** like $try */
                /** Tries to execute a number of functions.
                    Returns immediately the return value of the first
                    non-failed function without executing successive
                    functions, or null. **/
                attempt: function () {
                    var i, l;
                    for (i = 0, l = arguments.length; i < l; i += 1) {
                        try {
                            return arguments[i]();
                        } catch (e) {}
                    }
                    return null;
                },

                /** Turn a string into a function, like getattr in Python */
                get_function_from_string: function (fnname) {
                    var i, parts, lgth, fnref;
                    parts = fnname.split('.');
                    lgth = parts.length;
                    if (lgth === 1) {
                        return window[fnname];
                    }
                    fnref = window;
                    for (i = 0; i < lgth; i += 1) {
                        fnref = fnref[parts[i]];
                    }
                    return fnref;
                },

                // End of submodule FUNCTOOLS
            };
        }()),

        /** Functions for Elements and Nodes  */
        ELEMENT: (function () {
            return {
                /** Checks to see if supplied element contains
                    the supplied className -
                    works with multiple class names with space separaters*/
                has_className: function (element, className) {
                    var elementClassName;
                    if (MAG.TYPES.is_element(element)) {
                        elementClassName = element.className.toLowerCase();
                        return (elementClassName.length > 0 &&
                                (elementClassName === className.toLowerCase() ||
                                 new RegExp('(^| )' +
                                            className.toLowerCase() +
                                            '( |$)').test(elementClassName)));
                    }
                    return;
                },

                /** Adds supplied className to supplied element */
                add_className: function (element, className) {
                    var classNameString;
                    if (MAG.TYPES.is_element(element)) {
                        if (!MAG.ELEMENT.has_className(element, className)) {
                            classNameString = element.className += ' ' +
                                className;
                            element.className = MAG.TEMPLATE.trim(
                                classNameString
                            );
                        }
                    }
                    return element;
                },

                /** Removes supplied className from supplied element */
                remove_className: function (element, className) {
                    if (MAG.TYPES.is_element(element)) {
                        element.className = MAG.TEMPLATE.trim(
                            element.className.replace(
                                new RegExp('(^| )' + className + '( |$)'),
                                ' '
                            )
                        );
                    }
                    return element;
                },


                /** Checks it testnode is an ancestor of node (HTML tree) */
                is_ancestor: function (node, testnode) {
                    while (node && node.parentNode) {
                        if (node.parentNode === testnode) {
                            return true;
                        }
                        node = node.parentNode;
                    }
                    return false;
                },

                insertAfter: function (newElement,targetElement) {
                    var parent = targetElement.parentNode;
                    if(parent.lastchild == targetElement) {
                        parent.appendChild(newElement);
                    }
                    else {
                        parent.insertBefore(newElement, targetElement.nextSibling);
                    }
                }

                // End of submodule ELEMENT
            };
        }()),

        /** Tests for type.
            Checking types in Javascript is a big mess,
            this provides a consistent set of tests. */
        TYPES: (function () {
            return {
                //** Is the object an Array? */
                is_array: function (o) {
                    return Object.prototype.toString.call(o) ===
                        '[object Array]';
                },
                //** Is the object a String? */
                is_string: function (o) {
                    return typeof o === "string" ||
                        (typeof o === "object" && o.constructor === String);
                },
                /** Is the object an Object - e.g. a {} */
                is_object: function (o) {
                    return Object.prototype.toString.call(o) ===
                        '[object Object]';
                },
                is_empty_object: function (obj) {
                    var prop;
                    for (prop in obj) {
                        if (obj.hasOwnProperty(prop)) {
                            return false;
                        }
                    }
                    return true;
                },
                /** Is the object a Number */
                is_number: function (o) {
                    return Object.prototype.toString.call(o) ===
                        '[object Number]';
                },
                is_element: function (o) {
                    return o instanceof Element;
                },
                is_boolean: function (o) {
                    return Object.prototype.toString.call(o) ===
                        '[object Boolean]';
                }
                // End of submodule TYPES
            };
        }()),

        REST: (function () {
            return {

                /* Get the history for a single instance
                   resource - the resource type
                   id - the id of the instance
                   options - a dictionary of optional arguments:
                   options.success - callback function for success
                   options.error - callback function for error
                */
                get_history_for_instance: function (resource,
                                                    id,
                                                    options) {
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    options.method = "GET";
                    MAG._REQUEST.request(
                        MAG._STORAGE.get_data_from_storage_or_function(
                            "MAG._REST.get_api_url"
                        ) + '_history/?' + MAG.URL.build_query_string(
                            {
                                'document_model': resource,
                                'document_id': id
                            }
                        ),
                        options
                    );
                },

                /** Get a single history item by history id **/
                get_history_item: function (history_id,
                                            resource_type,
                                            options) {
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    options.method = "GET";
                    MAG._REQUEST.request(
                        MAG._STORAGE.get_data_from_storage_or_function(
                            "MAG._REST.get_api_url"
                        ) + '_history/' + history_id + '/?' +
                            MAG.URL.build_query_string(
                                {
                                    'document_model': resource_type,
                                }
                            ),
                        options
                    );
                },

                /** Check for existence.
                    I.e. HEAD

                    resource - the resource type
                    id - the id of the instance
                    options - a dictionary of optional arguments:
                    options.success - callback function for success
                    options.error - callback function for error
                */
                check_resource_existence: function (resource,
                                                    id,
                                                    options) {
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    options.method = "HEAD";
                    MAG._REQUEST.request(
                        MAG._STORAGE.get_data_from_storage_or_function(
                            "MAG._REST.get_api_simple_resource_instance_url",
                            resource + '/' + id,
                            [resource, id]
                        ),
                        options
                    );
                },

                /* Apply the callback function to a resource instance */
                /* I.e. GET */
                apply_to_resource: function (resource,
                                             id,
                                             options) {
                    var url, api_url, callback, request;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    if (typeof options.force_reload === 'undefined') {
                        options.force_reload = false;
                    }

                    // Make URL
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_simple_resource_instance_url",
                        resource + '/' + id,
                        [resource, id]
                    );
                    api_url = 'api:' + url;

                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        if (
                            !MAG._STORAGE.is_stored_item(api_url) ||
                                (options.force_reload === true)
                        ) {
                            options.success = MAG._REST.cache_api_data;
                        } // End if !(MAG._STORAGE.is_stored_item(api_url))

                    } else {
                        // We have an optional callback so use it.

                        if (
                            MAG._STORAGE.is_stored_item(api_url) &&
                                options.force_reload === false
                        ) {
                            options.success(
                                MAG._STORAGE.get_data_from_storage(api_url)
                            );
                            return;
                        }

                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.cache_api_data(data);
                            callback(data);
                        };
                    } // if (typeof optional_callback === 'undefined')
                    // So now we have a callback.

                    options.method = "GET";
                    MAG._REQUEST.request(url, options);
                },

                /* Get a list and optional callback, and cache the list
                   resource - resource type
                   options - optional arguments
                   - criteria - a SON object specifying elements which must
                   be present for a document to be included in
                   the result set
                   - fields - a list of field names that should be returned
                   in the result set (“_id” will always be included)
                   - force_reload - do not return any locally cached version

                */
                apply_to_list_of_resources: function (resource,
                                                      options) {
                    var base_url, url, api_url, full_url,
                    callback, request, criteria, query;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    if (typeof options.force_reload === 'undefined') {
                        options.force_reload = false;
                    }

                    base_url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_url"
                    );
                    url = base_url + resource + '/';

                    query = {}

                    if (typeof options.criteria !== 'undefined') {
                        query = options.criteria;
                        delete options.criteria;
                    }
                    if (typeof options.fields !== 'undefined') {
                        query['_fields'] = options.fields
                        delete options.fields;
                    }
                    if (!(MAG.TYPES.is_empty_object(query))) {
                        url += '?';
                        url += MAG.URL.build_query_string(query);
                    }

                    api_url = 'api:' + url;
                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource list
                        if (
                            MAG._STORAGE.is_stored_item(api_url)
                                && (options.force_reload === false)
                        ) {
                            // Nothing to do
                            return;
                        }
                        options.success = function (data) {
                            MAG._REST.cache_api_list(data,
                                                       resource,
                                                       criteria);
                        };
                    } else {
                        if (
                            MAG._STORAGE.is_stored_item(api_url) &&
                                options.force_reload === false
                        ) {
                            options.success(
                                MAG._STORAGE.get_data_from_storage(
                                    api_url
                                )
                            );
                            return;
                        }
                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.cache_api_list(data,
                                                       resource,
                                                       criteria);
                            callback(data);
                        };
                    } // End if (typeof optional_callback === 'undefined')

                    options.method = "GET";
                    MAG._REQUEST.request(url, options);
                },

                /* Create resource and cache the local copy
                   resource - the resource type
                   instance - the instance _id
                   options - optional arguments, including:
                   options.success - callback function for success
                   options.error - callback function for error
                   options.comment - optional comment
                */
                create_resource: function (resource,
                                           instance,
                                           options) {
                    var url, callback, request;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    /* Make a new instance */
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_url"
                    );
                    url += resource;
                    url += '/';

                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        options.success = MAG._REST.cache_api_data;
                    } else {
                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.cache_api_data(data);
                            callback(data);
                        };
                    } // End if (typeof optional_callback === 'undefined')

                    if (options.comment !== undefined) {
                        instance._versional_comment = options.comment;
                        delete options.comment;
                    }

                    options.method = "POST";
                    options.data = JSON.stringify(instance);
                    MAG._REQUEST.request(url,
                                           options);
                },

                /** Update resource and cache the local copy
                    resource - the resource type
                    instance - the instance object
                    options - optional arguments, including:
                    options.success - callback function for success
                    options.error - callback function for error
                    options.comment - optional comment
                */
                update_resource: function (resource,
                                           instance,
                                           options) {
                    // Make URL
                    var url, callback, api_url;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_simple_resource_instance_url",
                        resource + '/' + instance._id,
                        [resource, instance._id]
                    );

                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        options.success = MAG._REST.cache_api_data;
                    } else {
                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.cache_api_data(data);
                            callback(data);
                        };
                    } // End if (typeof optional_callback === 'undefined')

                    if (options.comment !== undefined) {
                        instance._versional_comment = options.comment;
                        delete options.comment;
                    }
                    options.data = JSON.stringify(instance);
                    options.method = "PUT";

                    MAG._REQUEST.request(url, options);
                },
                /** Delete multiple instances of a resource.
                    resource - the resource type
                    ids - ids of objects to be deleted
                    options - optional arguments, including:
                    options.success - callback function for success
                    options.error - callback function for error
                    options.comment - optional comment
                */

                delete_resources: function (resource,
                                            ids,
                                            options) {
                    var url, callback, request;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    options.data = {ids: ids};
                    if (options.comment !== undefined) {
                        options.data._versional_comment = options.comment;
                        delete options.comment;
                    }
                    options.data = JSON.stringify(options.data);

                    // Make URL
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_url"
                    ) + resource + '/';
                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just delete the resource
                        options.success = function () {
                            MAG._REST.delete_multiple_cached_data(
                                resource,
                                ids
                            );
                        };
                    } else {
                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.delete_multiple_cached_data(
                                resource,
                                ids
                            );
                            callback(data);
                        };
                    }
                    options.method = "DELETE";
                    MAG._REQUEST.request(url, options);
                },
                /** Update multiple instances of a resource,
                    in this method.

                    The difference between this and the method below,
                    is that the method below requires a list of ids,
                    this method requires a list of whole instances.

                    resource - the resource type
                    instances - an array of updated instances
                    options - optional arguments, including:
                    options.success - callback function for success
                    options.error - callback function for error
                    options.comment - optional comment
                */
                update_resources: function (resource,
                                            instances,
                                            options) {
                    var url, callback, options_data;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_url"
                    ) + resource + '/';

                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        options.success = MAG._REST.cache_multiple_instances;
                    } else {
                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.cache_multiple_instances(data);
                            callback(data);
                        };
                    } // End if (typeof optional_callback === 'undefined')
                    options_data = {instances: instances};
                    if (options.comment !== undefined) {
                        options_data._versional_comment = options.comment;
                        delete options.comment;
                    }
                    options.data = JSON.stringify(options_data);
                    options.method = "PUT";
                    MAG._REQUEST.request(url, options);
                },

                /** Update a field or fields in multiple instances
                    of a resource.

                    The difference between this and the method above,
                    is that the method above requires the whole instance
                    to be provided, while this method requires a list
                    of ids and a fields object.

                    resource - the resource type.
                    ids - an array of ids that are to be updated.
                    fields - an object containing the fields to be updated,
                    in update modifier format.
                    See http://www.mongodb.org/display/DOCS/Updating#Updating-ModifierOperations for more information

                    Any Key,value pair without an update modifier keyword
                    (e.g. $set, $inc, etc) is assumed
                    to be {$set: {key, value}

                    options - optional arguments, including:
                    options.success - callback function for success
                    options.error - callback function for error
                    options.comment - optional comment
                */
                update_fields: function (resource,
                                         ids,
                                         fields,
                                         options) {
                    var url, callback, options_data;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_url"
                    ) + resource + '/';
                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        options.success = MAG._REST.cache_multiple_instances;
                    } else {
                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.cache_multiple_instances(data);
                            callback(data);
                        };
                    } // End if (typeof optional_callback === 'undefined')

                    options_data = {fields: fields,
                                    ids: ids};
                    if (options.comment !== undefined) {
                        options_data._versional_comment = options.comment;
                        delete options.comment;
                    }
                    options.data = JSON.stringify(options_data);
                    options.method = "PUT";
                    MAG._REQUEST.request(url, options);
                },

                /** Update a field or fields in multiple instances
                    of a resource.

                    The difference between this and the method above,
                    is that this requires a critera object.

                    resource - the resource type.
                    criteria - key/value pairs that match.
                    fields - an object containing the fields to be updated,
                    in update modifier format.
                    See http://www.mongodb.org/display/DOCS/Updating#Updating-ModifierOperations for more information

                    Any Key,value pair without an update modifier keyword
                    (e.g. $set, $inc, etc) is assumed
                    to be {$set: {key, value}

                    options - optional arguments, including:
                    options.success - callback function for success
                    options.error - callback function for error
                    options.comment - optional comment
                */
                update_field_selection: function (resource,
                                                  criteria,
                                                  fields,
                                                  options) {
                    var url, callback, options_data;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_url"
                    ) + resource + '/';
                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        options.success = MAG._REST.cache_multiple_instances;
                    } else {
                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.cache_multiple_instances(data);
                            callback(data);
                        };
                    } // End if (typeof optional_callback === 'undefined')

                    options_data = {fields: fields,
                                    criteria: criteria};
                    if (options.comment !== undefined) {
                        options_data._versional_comment = options.comment;
                        delete options.comment;
                    }
                    options.data = JSON.stringify(options_data);
                    options.method = "PUT";
                    MAG._REQUEST.request(url, options);
                },

                /* Delete a resource from server, and local copy */
                delete_resource: function (resource,
                                           id,
                                           options) {
                    var url, callback, request;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    // Make URL
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_simple_resource_instance_url",
                        resource + '/' + id,
                        [resource, id]
                    );
                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just delete the resource
                        options.success = MAG._REST.delete_api_data;
                    } else {
                        callback = options.success;
                        options.success = function (data) {
                            MAG._REST.delete_api_data(data);
                            callback(data);
                        };
                    }
                    options.method = "DELETE";
                    MAG._REQUEST.request(url, options);
                }
                // End of submodule
            };
        }()),

        /** Advanced REST Commands */
        COMMAND: (function () {
            return {

                /* If the id argument is unique it is returned,
                   if it is not-unique it is made unique and returned.
                   resource = resource type
                   id = id to be unique
                   options.success - callback on success

                */
                get_unique_id: function (resource,
                                         id,
                                         options) {
                    var url, api_url, callback, request;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    if (typeof options.success === 'undefined') {
                        options.success = function () {};
                    }
                    // Make URL
                    url = MAG._STORAGE.get_data_from_storage_or_function(
                        "MAG._REST.get_api_simple_resource_instance_url",
                        resource + '/' + id,
                        [resource, id]
                    ) + 'uniquify/';
                    api_url = 'api:' + url;
                    options.method = "GET";
                    MAG._REQUEST.request(url, options);
                }
                // End of submodule
            };
        }()),

        AUTH: (function () {
            return {

                /** Log the user out. */
                log_user_out: function (next) {
                    localStorage.clear();
                    if (typeof next === "undefined") {
                        next = '/';
                    }
                    window.location.href = "/auth/logout/?next=" + next;
                },

                /** Log the user in. */
                log_user_in: function (next) {
                    var item;
                    if (typeof next === "undefined") {
                        next = '/';
                    }
                    window.location.href = "/auth/login/?next=" + next;
                    /* Get rid of any permissions in localStorage */
                    for (item in localStorage) {
                        if (localStorage.hasOwnProperty(item)) {
                            if (item.indexOf('/auth/') !== -1) {
                                delete localStorage[item];
                            }
                        }
                    }
                },
                /** Get user info
                    options - dictionary of optional arguments:
                    options.success
                    options.error
                    options.force_reload

                */
                get_user_info: function (options) {
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    var url, api_url, callback;
                    if (typeof options.force_reload === 'undefined') {
                        options.force_reload = false;
                    }
                    url = 'http://' + SITE_DOMAIN;
                    url += '/auth/whoami/';
                    api_url = 'api:' + url;

                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        if (
                            MAG._STORAGE.is_stored_item(api_url) &&
                                (options.force_reload === false)
                        ) {
                            // Nothing to do
                            return;
                        }
                        options.success = function (data) {
                            MAG._STORAGE.store_data(api_url, data);
                        };
                    } else {
                        // We have an optional callback so use it.
                        if (
                            MAG._STORAGE.is_stored_item(api_url) &&
                                options.force_reload === false
                        ) {
                            options.success(
                                MAG._STORAGE.get_data_from_storage(api_url)
                            );
                            return;
                        }
                        callback = options.success;
                        options.success = function (data) {
                            MAG._STORAGE.store_data(api_url, data);
                            callback(data);
                        };
                    } // if (typeof optional_callback === 'undefined')
                    // So now we have a callback.
                    options.method = "GET";
                    MAG._REQUEST.request(url, options);
                },

                /** Check permission
                    resource - resource name,
                    permission - either 'read', 'create', 'update', 'delete'

                    permissions can be set per resource or per user+resource.

                    options.success
                    options.error
                    options.force_reload

                */
                check_permission: function (resource,
                                            permission,
                                            options) {
                    var path, url, api_url, callback;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    if (typeof options.force_reload === 'undefined') {
                        options.force_reload = false;
                    }

                    path = MAG.TEMPLATE.substitute(
                        "/auth/checkpermission/{resource}/{permission}/",
                        {resource: resource, permission: permission}
                    );

                    url = 'http://' + SITE_DOMAIN;
                    url += path;
                    api_url = 'api:' + url;
                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        if (
                            MAG._STORAGE.is_stored_item(api_url) &&
                                (options.force_reload === false)
                        ) {
                            // Nothing to do
                            return;
                        }
                        options.success = function (data) {
                            MAG._STORAGE.store_data(api_url, data);
                        };
                    } else {
                        // We have an optional callback so use it.
                        if (
                            MAG._STORAGE.is_stored_item(api_url) &&
                                options.force_reload === false
                        ) {
                            options.success(
                                MAG._STORAGE.get_data_from_storage(api_url)
                            );
                            return;
                        }
                        callback = options.success;
                        options.success = function (data) {
                            MAG._STORAGE.store_data(api_url, data);
                            callback(data);
                        };
                    } // if (typeof optional_callback === 'undefined')
                    // So now we have a callback.
                    options.method = "GET";
                    MAG._REQUEST.request(url, options);
                },
                /** Check permissions

                    Returns boolean and missing permissions.
                    So if all permissions match, it returns true and an
                    empty object.
                    If not all permissions match, it returns false and an
                    object of the missing permissions.

                    resource - resource name,
                    permissions - an object with each entry having a
                    resource type as the key, and a list of permissions
                    as the values, e.g.
                    {'author': ['read', 'create', 'update', 'delete']}
                    options.success
                    options.error
                    options.force_reload

                */
                check_permissions: function (permissions,
                                             options) {
                    var url, api_url, query_string, callback;
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    if (typeof options.force_reload === 'undefined') {
                        options.force_reload = false;
                    }
                    query_string = MAG.URL.build_query_string(permissions);

                    url = 'http://' + SITE_DOMAIN + '/auth/checkpermission/?' +
                        query_string;
                    api_url = 'api:' + url;
                    if (typeof options.success === 'undefined') {
                        // No optional callback
                        // Just cache the resource
                        if (
                            MAG._STORAGE.is_stored_item(api_url) &&
                                (options.force_reload === false)
                        ) {
                            // Nothing to do
                            return;
                        }
                        options.success = function (data) {
                            MAG._STORAGE.store_data(api_url, data);
                        };
                    } else {
                        // We have an optional callback so use it.
                        if (
                            MAG._STORAGE.is_stored_item(api_url) &&
                                options.force_reload === false
                        ) {
                            options.success(
                                MAG._STORAGE.get_data_from_storage(api_url)
                            );
                            return;
                        }
                        callback = options.success;
                        options.success = function (data) {
                            MAG._STORAGE.store_data(api_url, data);
                            callback(data);
                        };
                    } // if (typeof optional_callback === 'undefined')
                    // So now we have a callback.
                    options.method = "GET";
                    MAG._REQUEST.request(url, options);
                }
                // End of submodule AUTH
            };
        }()),

        /** Functions dealing with URLs */
        URL: (function () {
            return {
                get_home_url: function () {
                    return 'http://' + SITE_DOMAIN + '/';
                },

                get_static_url: function () {
                    return MAG.URL.get_home_url() + 'static/';
                },

                /** Returns the current query arguments as an object of key,
                    value pairs. */
                get_current_query: function () {
                    if (
                        window.location.search === "" ||
                            window.location.search === "?"
                    ) {
                        return {};
                    }
                    return MAG.URL.parse_query_string(window.location.search);
                },

                /** Add an argument to a an existing URL */
                add_argument_to_url: function (url, key, value) {
                    var template;
                    if (MAG.URL.contains_question_mark(url)) {
                        template = "{url};{key}={value}";
                    } else {
                        template = "{url}?{key}={value}";
                    }
                    return MAG.TEMPLATE.substitute(template,
                                                     {url: url,
                                                      key: key,
                                                      value: value});
                },

                /** Encode a object of fields to a query /
                    Required Argument:
                    data - the data to be encoded
                */
                build_query_string: function (data) {
                    var query_arg, ret, value, json_value;
                    ret = [];
                    for (query_arg in data) {
                        if (data.hasOwnProperty(query_arg)) {
                            value = data[query_arg];
                            if (
                                MAG.TYPES.is_string(value)
                            ) {
                                ret.push(
                                    encodeURIComponent(query_arg) +
                                        "=" + encodeURIComponent(value)
                                );
                            } else {
                                json_value = JSON.stringify(value);
                                ret.push(
                                    encodeURIComponent(query_arg) + "=" +
                                        "JSON:" + encodeURIComponent(
                                            json_value
                                        )
                                );
                                //if (json_value === String(value)) {
                                //    ret.push(encodeURIComponent(query_arg) +
                                //"=" + encodeURIComponent(value));
                                //} else {
                                //    ret.push(encodeURIComponent(query_arg) +
                                //"=" + "JSON:"
                                //+ encodeURIComponent(json_value));
                                //}
                            }
                        }
                    }
                    return ret.join(";");
                },

                /** Turns a querystring into an object of key/value pairs.
                    Required Argument:
                    querystring - the querystring to be parsed
                    Optional Arguments:
                    strip_leading_question_mark - (boolean, optional) if set
                    to false, any leading question mark is not removed.
                    decodeKeys - (boolean, optional) if set to false,
                    keys are passed through [decodeURIComponent][]; defaults
                    to true
                    decodeValues - (boolean, optional) if set to false, values
                    are passed through [decodeURIComponent][]; defaults to true
                */
                parse_query_string: function (querystring,
                                              strip_leading_question_mark,
                                              decodeKeys,
                                              decodeValues) {
                    var vars, object, i, length;
                    if (typeof querystring === "undefined") {
                        throw new TypeError(
                            "querystring is a required argument."
                        );
                    }
                    if (
                        (typeof decodeKeys === "undefined") ||
                            (decodeKeys === null)
                    ) {
                        decodeKeys = true;
                    }
                    if (
                        (typeof decodeValues === "undefined") ||
                            (decodeValues === null)
                    ) {
                        decodeValues = true;
                    }
                    if (typeof strip_leading_question_mark === "undefined") {
                        strip_leading_question_mark = true;
                    }
                    if (
                        strip_leading_question_mark &&
                            querystring.charAt(0) === '?'
                    ) {
                        querystring = querystring.substring(1);
                    }
                    vars = querystring.split(/[&;]/);
                    object = {};
                    if (!vars.length) {
                        return object;
                    }

                    vars.map(function (val) {
                        var index, value, keys, obj;
                        index = val.indexOf('=') + 1;
                        value = index ? val.substr(index) : '';
                        keys = index ? val.substr(
                            0,
                            index - 1
                        ).match(
                                /([A-Za-z0-9_\-\.\,\?\$\(\)\*\+~\/@\ ]+|(\B)(?=\]))/g
                        ) : [val];
                        obj = object;
                        if (!keys) {
                            return;
                        }
                        if (decodeValues) {
                            value = decodeURIComponent(value);
                        }
                        if (MAG.TYPES.is_string(value)) {
                            if (value.indexOf('JSON:') === 0) {
                                value = value.substr(5);
                                value = JSON.parse(value);
                            }
                        }
                        keys.map(function (key, i) {
                            var current;
                            if (decodeKeys) {
                                key = decodeURIComponent(key);
                            }
                            current = obj[key];

                            if (i < keys.length - 1) {
                                obj = obj[key] = current || {};
                            } else if (MAG.TYPES.is_array(current)) {
                                current.push(value);
                            } else {
                                if (typeof current === 'undefined') {
                                    obj[key] = value;
                                } else {
                                    obj[key] = [current, value];
                                }
                            }
                        });
                    });

                    return object;
                },
                /** Tests whether a URL has a query,
                    i.e. whether a string has a question mark */
                contains_question_mark: function (url) {
                    if (url.indexOf('?') === -1) {
                        return false;
                    }
                    return true;
                }

                // End of submodule URL
            };
        }()),

        _REST: (function () {
            return {
                // Body of submodule here
                get_api_url: function () {
                    return 'http://' + SITE_DOMAIN + '/api/';
                },

                get_api_query_url: function () {
                    return MAG._STORAGE.get_data_from_storage_or_function(
                        'MAG._REST.get_api_url',
                        '',
                        ''
                    ) + 'query/?';
                },

                get_api_simple_resource_instance_url: function (resource, id) {
                    var api_url =
                        MAG._STORAGE.get_data_from_storage_or_function(
                            'MAG._REST.get_api_url',
                            '',
                            ''
                        );
                    return api_url + resource + '/' + id + '/';
                },
                /** Cache the api data into the localStorage */
                cache_api_data: function (data) {
                    var storagekey;
                    storagekey = "api:" +
                        MAG._STORAGE.get_data_from_storage_or_function(
                            "MAG._REST.get_api_simple_resource_instance_url",
                            data._model + '/' + data._id,
                            [data._model, data._id]
                        );
                    MAG._STORAGE.store_data(storagekey, data);
                },

                /** Cache multiple instances individually.
                    Expects an object with key instances with
                    a value array of instances. */
                cache_multiple_instances: function (data) {
                    var length, i;
                    length = data.instances.length;
                    for (i = 0; i < length; i += 1) {
                        MAG._REST.cache_api_data(data.instances[i]);
                    }
                },

                /** Cache list data with an optional query argument */
                cache_api_list: function (data, resource, query) {
                    var storagekey;
                    storagekey = "api:" +
                        MAG._STORAGE.get_data_from_storage_or_function(
                            "MAG._REST.get_api_url"
                        ) + resource + '/';
                    if (typeof query !== 'undefined') {
                        storagekey += '?' + MAG.URL.build_query_string(query);
                    }
                    MAG._STORAGE.store_data(storagekey, data);
                },

                /** Delete cached data */
                delete_api_data: function (data) {
                    var storagekey;
                    storagekey = "api:" +
                        MAG._STORAGE.get_data_from_storage_or_function(
                            "MAG._REST.get_api_simple_resource_instance_url",
                            data._model + '/' + data._id,
                            [data._model, data._id]
                        );
                    if (localStorage[storagekey] !== 'undefined') {
                        delete localStorage[storagekey];
                    }
                },
                /** Delete multiple cached data by ids */
                delete_multiple_cached_data: function (resource, ids) {
                    var storagekey, instance_key, length, i;
                    storagekey = "api:" +
                        MAG._STORAGE.get_data_from_storage_or_function(
                            "MAG._REST.get_api_url"
                        ) + resource + '/';
                    length = ids.length;
                    for (i = 0; i < length; i += 1) {
                        instance_key = storagekey + ids[i] + '/';
                        if (localStorage[instance_key] !== 'undefined') {
                            delete localStorage[instance_key];
                        }
                    }
                }
                // End of submodule _REST
            };
        }()),


        _REQUEST: (function () {
            return {
                //progressSupport: ('onprogress' in new Browser.Request),

                /** Send a request, given string data where appropriate */
                request: function (url,
                                   options) {
                    if (typeof options === "undefined") {
                        options = {};
                    }
                    if (typeof options.method === "undefined") {
                        options.method = "GET";
                    }

                    var xhr, trimPosition, header, default_headers;

                    // Remove any hash fragment in the URL
                    trimPosition = url.lastIndexOf('/');
                    if (
                        trimPosition > -1 &&
                            (trimPosition = url.indexOf('#')) > -1
                    ) {
                        url = url.substr(0, trimPosition);
                    }
                    // IE needs a special JSON bit in the URL
                    if (
                        MAG._REQUEST.detect_ie()
                    ) {
                        url = MAG.URL.add_argument_to_url(
                            url,
                            'format',
                            'json'
                        );
                    }
                    // Instantiate the xhr
                    xhr = MAG._REQUEST._xhr();
                    /*
                      if (progressSupport){
                      xhr.onloadstart = this.loadstart.bind(this);
                      xhr.onprogress = this.progress.bind(this);
                      }
                    */

                    /** Open the request.
                        See https://developer.mozilla.org/en/
                        XMLHttpRequest#open%28%29
                    */
                    xhr.open(options.method.toUpperCase(),
                             url,
                             true,
                             options.user,
                             options.password);

                    /** Turns on autentication if required. */
                    if (
                        (typeof options.user !== 'undefined') &&
                            (typeof xhr.hasOwnProperty !== 'undefined')
                    ) {
                        xhr.withCredentials = true;
                    }
                    /** Set up the success callback */
                    xhr.onreadystatechange = function () {
                        if (xhr.readyState !== 4) {
                            return;
                        }
                        if (
                            (xhr.status >= 200 && xhr.status < 300) ||
                                xhr.status === 304
                        ) {
                            if (typeof options.success !== 'undefined') {
                                if (xhr.responseText === "") {
                                    options.success(true);
                                } else {
                                    options.success(
                                        JSON.parse(xhr.responseText, true)
                                    );
                                }
                            } else {
                                // No callback, do nothing
                                return;
                            }
                        } else {
                            // Not successful
                            if (typeof options.error !== 'undefined') {
                                options.error(xhr);
                            }
                        }
                    };

                    default_headers = MAG._REQUEST._default_headers;
                    /* Set the values of the HTTP request headers. */
                    for (header in default_headers) {
                        if (default_headers.hasOwnProperty(header)) {
                            xhr.setRequestHeader(
                                header,
                                default_headers[header]
                            );
                        }
                    }

                    // Add the charset
                    if (
                        ['POST', 'PUT'].indexOf(
                            options.method.toUpperCase()
                        ) !== -1
                    ) {
                        xhr.setRequestHeader(
                            'Content-type',
                            'application/x-www-form-urlencoded; charset=utf8'
                        );
                    }
                    xhr.send(options.data);
                    return xhr;
                },

                _default_headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'X-Request': 'JSON'
                },

                /** The XMLHTTP object or equivalent. */
                /** was Browser.Request */
                _xhr: function () {
                    return MAG.FUNCTOOLS.attempt(function () {
                        return new XMLHttpRequest();
                    }, function () {
                        return new ActiveXObject('MSXML2.XMLHTTP');
                    }, function () {
                        return new ActiveXObject('Microsoft.XMLHTTP');
                    });
                },

                /** Attempt to detect Internet Explorer,
                    if successful return the version. */
                detect_ie: function () {
                    return (
                        !window.ActiveXObject
                    ) ? false : (
                        (window.XMLHttpRequest) ? (
                            (
                                document.querySelectorAll
                            ) ? 6 : 5
                        ) : 4
                    );
                }

                // End of submodule _REQUEST
            };
        }()),

        TEMPLATE: (function () {
            return {

                /** Performs a template substitution, returning a new string.
                    mapping is an object with keys that match the placeholders
                    in the template. */
                substitute: function (template, mapping) {
                    return template.replace(
                        (/\\?\{([A-Za-z0-9_\-]+)\}/g),
                        function (match, name) {
                            //return template.replace((/\\?\{([^{}]+)\}/g),
                            //function (match, name) {
                            if (match.charAt(0) === '\\') {
                                return match.slice(1);
                            }
                            return (
                                mapping[name] !== null
                            ) ? mapping[name] : '';
                        }
                    );
                },

                /** Removes leading and trailing white space from string and
                 * reduces multiple white space internally to a single space*/
                trim: function (s) {
                    s = s.replace(/(^\s*)|(\s*$)/gi, "");
                    s = s.replace(/[ ]{2,}/gi, " ");
                    s = s.replace(/\n /, "\n");
                    return s;
                },

                /** Replace all instances of `old_key` in `string` with `new_key` */
                replace_all: function(string, old_key, new_key) {
                    var regex = new RegExp(old_key, 'g');
                    return string.replace(regex, new_key);
                },
                // End of submodule TEMPLATE
            };
        }()),


        _STORAGE: (function () {
            return {
                // Body of submodule here

                supports_local_storage: function () {
                    // Returns true if we have storage
                    if (typeof window.localStorage === "undefined") {
                        return false;
                    }
                    return true;
                },

                is_stored_item: function (key) {
                    // Check to see if the local storage has an item
                    if (!MAG._STORAGE.supports_local_storage()) {
                        return false;
                    }
                    if (localStorage[key]) {
                        return true;
                    }
                    return false;
                },

                /** Put data into local storage */
                store_data: function (storagekey, data, type, serialiser) {
                    var storedata, storage_object;
                    if (typeof type === "undefined") {
                        type = 'json';
                    }
                    if (typeof serialiser !== "undefined") {
                        storedata = serialiser(data);
                    } else {
                        storedata = data;
                    }
                    storage_object = {'type': type,
                                      'data': storedata,
                                      'timestamp': new Date().getTime()
                                     };
                    localStorage[storagekey] = JSON.stringify(storage_object);
                },

                /** Get data from storage, by key */
                get_data_from_storage: function (storagekey, deserialiser) {
                    var json_object, storage_object;
                    json_object = localStorage[storagekey];
                    storage_object = JSON.parse(json_object);
                    if (typeof deserialiser === "undefined") {
                        return storage_object.data;
                    }
                    return deserialiser(storage_object.data);
                },

                /** Try storage, if not execute the function */
                get_data_from_storage_or_function: function (
                    fnname,
                    keyarg,
                    fnarg
                ) {
                    var storagekey, storage_object, data, result;
                    storagekey = MAG.TEMPLATE.substitute(
                        "{fnname}:{keyarg}",
                        {
                            'fnname': fnname,
                            'keyarg': keyarg
                        }
                    );
                    if (MAG._STORAGE.is_stored_item(storagekey)) {
                        return MAG._STORAGE.get_data_from_storage(storagekey);
                    }
                    // Not in storage (yet)
                    // Multiple arguments or single argument
                    if (fnarg instanceof Array) {
                        result = MAG.FUNCTOOLS.get_function_from_string(
                            fnname
                        ).apply(this, fnarg);
                    } else {
                        result = MAG.FUNCTOOLS.get_function_from_string(
                            fnname
                        )(fnarg);
                    }
                    MAG._STORAGE.store_data(storagekey, result);
                    return result;
                },

                /** Remove everything after the delimiter, defaults to - */
                ditch_prefix: function (argstring, delimiter) {
                    var components, parts;
                    delimiter = (
                        typeof delimiter === "undefined"
                    ) ? '-' : delimiter;
                    components = argstring.split(delimiter);
                    parts = ([components.shift(), components.join(delimiter)]);
                    return parts[1];
                }

                // End of submodule _STORAGE
            };
        }()),

        EVENT: (function () {
            return {

                add_event: function (element, type, fn, nickname) {
                    if (typeof MAG._EVENT_STORE[nickname] === "undefined") {
                        MAG._EVENT_STORE[nickname] = [];
                    }

                    MAG._EVENT_STORE[nickname].push(
                        {
                            'element': element,
                            'type': type,
                            'fn': fn
                        }
                    );
                    MAG.EVENT.addEventListener(element, type, fn);
                },

                /** Remove an event by nickname,
                    Required: nickname - the given name of the event
                    Options:
                    options.type - type of event e.g. click
                    options.element - the element the event is attached to.
                */
                remove_event: function (nickname, options) {
                    var i, event;
                    if (typeof options === "undefined") {
                        options = {};
                    }

                    if (typeof MAG._EVENT_STORE[nickname] === "undefined") {
                        return;
                    }
                    for (i = MAG._EVENT_STORE[nickname].length - 1; i >= 0; i = i - 1) {
                        event = MAG._EVENT_STORE[nickname][i];
                        if (options.type) {
                            if (event.type !== options.type) {
                                continue;
                            }
                        }
                        if (options.element) {
                            if (event.element !== options.element) {
                                continue;
                            }
                        }

                        MAG.EVENT.removeEventListener(
                            event.element,
                            event.type,
                            event.fn
                        );
                        MAG._EVENT_STORE[nickname].splice(i, 1);
                    }
                    if (MAG._EVENT_STORE[nickname].length === 0) {
                        delete MAG._EVENT_STORE[nickname];
                    }
                },

                /** attachEvent is used for IE8 (and below),
                    addEventListener is called for IE9+ and everyone else,
                    Note that IE6 and IE7 leak can leak memory here.
                    Consider explicitly writing the functions to a stack
                    and deleting them as frameworks do.
                */
                addEventListener: function (element, type, fn) {
                    if (element.addEventListener) {
                        element.addEventListener(type, fn, false);
                    } else if (element.attachEvent) {
                        element.attachEvent('on' + type, fn);
                    }
                },

                removeEventListener: function (element, type, fn) {
                    if (element.removeEventListener) {
                        element.removeEventListener(type, fn, false);
                    } else if (element.detachEvent) {
                        element.detachEvent('on' + type, fn);
                    }
                },

                /** Which HTML element is the target of the event? */
                get_event_target: function (e) {
                    var targ;
                    if (!e) {
                        e = window.event;
                    }
                    if (e.target) {
                        targ = e.target;
                    } else if (e.srcElement) {
                        targ = e.srcElement;
                    }
                    if (targ.nodeType === 3) {
                        // defeat Safari bug
                        targ = targ.parentNode;
                    }
                    return targ;
                }

                // End of submodule _EVENT
            };
        }()),

        TABLE: (function () {
            return {
                TEMPLATES: {
                    'table_outer': '<table class="sortable" id="{id}" ' +
                        'cellpadding="0" cellspacing="0">\n{tableconte' +
                        'nt}\n</table>',
                    'table_row': '<tr>{rowcontent}</tr>',
                    'table_item': '<td>{itemcontent}</td>',
                    'table_header': '<th>{headercontent}</th>'
                },

                get_row: function (row_content) {
                    return MAG.TEMPLATE.substitute(
                        MAG.TABLE.TEMPLATES.table_row,
                        {'rowcontent': row_content}
                    );
                },

                get_item_as_string: function (name, object) {
                    if (MAG.TYPES.is_string(object)) {
                        return object;
                    }
                    if (MAG.TYPES.is_object(object)) {
                        if (name === '_id') {
                            if (object.$oid !== "undefined") {
                                return object.$oid;
                            }
                        }
                    }
                    // If we got here then we do not know what object is.
                    return object;
                },

                get_item: function (item_content) {
                    return MAG.TEMPLATE.substitute(
                        MAG.TABLE.TEMPLATES.table_item,
                        {'itemcontent': item_content}
                    );
                },

                get_table: function (table_content, id) {
                    if (typeof id === 'undefined') {
                        id = "sortable";
                    }
                    return MAG.TEMPLATE.substitute(
                        MAG.TABLE.TEMPLATES.table_outer,
                        {
                            'tablecontent': table_content,
                            "id": id
                        }
                    );
                },

                get_table_header: function (data) {
                    var header_data, name, row_data;
                    header_data = "";
                    for (name in data[0]) {
                        if (typeof data[0][name] !== 'function') {
                            header_data += MAG.TEMPLATE.substitute(
                                MAG.TABLE.TEMPLATES.table_header,
                                {'headercontent': name}
                            );
                        } // End if (typeof data[i][name] !== 'function')
                    } // End: for (name in data[i])
                    return MAG.TABLE.get_row(header_data);
                },

                show_table: function (data) {
                    var i, content, name, row_data;
                    content = MAG.TABLE.get_table_header(data);
                    // Go through each row in data
                    for (i = 0; i < data.length; i += 1) {
                        row_data = "";
                        // Go through each item in row
                        for (name in data[i]) {
                            if (typeof data[i][name] !== 'function') {
                                row_data += MAG.TABLE.get_item(
                                    MAG.TABLE.get_item_as_string(
                                        name,
                                        data[i][name]
                                    )
                                );
                            } // End if (typeof data[i][name] !== 'function')
                        } // End: for (name in data[i])
                        // Put the row together
                        content += MAG.TABLE.get_row(row_data);
                    } // End: for (i = 0; i < data.length; i += 1)

                    return MAG.TABLE.get_table(content);
                }, // End: show_table

                /** Make a table cell editable */
                make_editable: function (cell) {
                    var input, text;
                    // Check the node is not already editable
                    if (cell.nodeName.toUpperCase() !== "INPUT") {
                        input = document.createElement("INPUT");
                        input.value = cell.firstChild.nodeValue;
                        input.style.background = "rgb(255,244,255)";
                        cell.replaceChild(input, cell.firstChild);
                        cell.firstChild.select();
                        cell.firstChild.focus();
                    } else {
                        text = document.createTextNode(cell.firstChild.value);
                        cell.replaceChild(text, cell.firstChild);
                    }
                },
                make_table_edit_event: function (table_id) {
                    MAG.EVENT.addEventListener(
                        document.getElementById(table_id),
                        'click',
                        function (event) {
                            MAG.TABLE.handle_table_edit_click(
                                event,
                                table_id
                            );
                        }
                    );
                },
                find_header_for_cell: function (table_element,
                                                cell_element) {
                    return table_element.getElementsByTagName('th')[
                        cell_element.cellIndex
                    ];
                },

                handle_table_edit_click: function (event, table_id) {
                    var table_element, cell_element, header;
                    table_element = document.getElementById(table_id);
                    cell_element = MAG.EVENT.get_event_target(event);

                    // Perhaps should be id or something instead
                    header = MAG.TABLE.find_header_for_cell(
                        table_element,
                        cell_element
                    ).textContent;
                    if (cell_element.tagName.toUpperCase() === 'TH') {
                        // It is a header, probably do something different.
                        console.log('header');
                        // TODO
                    } else if (cell_element.tagName.toUpperCase() === 'TD') {
                        // It is a normal cell, make it editable
                        MAG.TABLE.make_editable(cell_element);
                    }
                }

                // End of submodule TABLE
            };
        }()),

        ADMIN: (function () {
            return {
                init: function () {
                    MAG.ADMIN.open_page();
                },
                PAGES: {'users': 'MAG.ADMIN.show_user_page'},

                show_admin_home: function () {
                    document.getElementById('content').innerHTML = "Admin Home";
                },

                show_user_page: function () {
                    MAG.ADMIN.get_users();
                },

                show_user_table: function (users) {
                    document.getElementById('content').innerHTML =
                        MAG.TABLE.show_table(users.results);
                },

                get_users: function () {
                    MAG.REST.apply_to_list_of_resources(
                        '_user',
                        {success: MAG.ADMIN.show_user_table}
                    );
                },

                open_page: function () {
                    var page, fn_name, query;
                    query = MAG.URL.get_current_query();
                    if (!query) {
                        return MAG.ADMIN.show_admin_home;
                    }
                    page = query['*page'];
                    if (page) {
                        fn_name = MAG.ADMIN.PAGES[page];
                        if (typeof fn_name !== "undefined") {
                            MAG.FUNCTOOLS.get_function_from_string(fn_name)();
                        }
                    }
                    return MAG.ADMIN.show_admin_home;
                }
                // End of submodule ADMIN
            };
        }()),

        FORMS: (function () {
            return {

                /** validate a form to check all fields with required
                    className are complete
                    and all data entered conforms to type required by
                    className attribute on element */
                validate_form: function (form_id) {
                    var i, elems, missing_list, invalid_list, result;
                    missing_list = [];
                    invalid_list = [];
                    elems = document.getElementById(form_id).elements;
                    for (i = 0; i < elems.length; i += 1) {
                        result = MAG.FORMS.validate_element(elems[i]);
                        if (result.invalid === true) {
                            invalid_list.push(elems[i].id);
                        }
                        if (result.missing === true) {
                            missing_list.push(elems[i].id);
                        }
                    }
                    if (missing_list.length === 0 && invalid_list.length === 0) {
                        return {'result': true, 'missing': missing_list, 'invalid': invalid_list};
                    }
                    return {'result': false, 'missing': missing_list, 'invalid': invalid_list};
                },

                /** */
                validate_element: function (elem) {
                    var missing, invalid;
                    missing = false;
                    invalid = false;
                    //only need to type validate free text fields input
                    //type=text and textarea and only
                    //if we don't require strings
                    if ((elem.tagName === 'INPUT' && elem.type === 'text') ||
                        elem.tagName === 'TEXTAREA') {
                        if (MAG.ELEMENT.has_className(elem, 'integer') &&
                            elem.value.length > 0) {
                            if (isNaN(parseInt(elem.value, 10))) {
                                invalid = true;
                            }
                        }
                    }
                    //check required fields are not empty or none
                    if (
                        MAG.ELEMENT.has_className(elem, 'required') &&
                            (elem.value === '' || elem.value === 'none')
                    ) {
                        missing = true;
                    }
                    return {'missing': missing, 'invalid': invalid};
                },


                /** Populate a select
                 * data = list of json objects containing all data or a list of strings which will be used as value and display
                 * select = HTML element to be populated
                 * value_key = a single key as a string to use as value attribute for option
                 * text_keys = a string, list of strings or object with numbered keys, to use as text of option,
                 *              falls through list until it finds one in the data or comma separates numbered fields is object
                 * selected_option_value = optional argument to say which of the options should be selected */
                populate_select: function (data, select, value_key, text_keys, selected_option_value) {
                    var options, i, j, template, mapping, text_key, inner_template, inner_template_list, option_text, inner_mapping;
                    options = '<option value="none">select</option>';
                    template = '<option value="{val}"{select}>{text}</option>';
                    for (i = 0; i < data.length; i += 1) {
                        //sort out fall through to a key which does exist if text_keys is an array
                        if (MAG.TYPES.is_array(text_keys)) {
                            for (j = 0; j < text_keys.length; j += 1) {
                                if (data[i].hasOwnProperty(text_keys[j])) {
                                    text_key = text_keys[j];
                                    break;
                                }
                            }
                        } else {
                            text_key = text_keys;
                        }
                        //if text_key is an object map multiple keys to display in option
                        if (MAG.TYPES.is_object(text_key)) {
                            inner_template_list = [];
                            j = 1;
                            inner_mapping = {};
                            while (text_key.hasOwnProperty(j)) {
                                inner_template_list.push('{' + text_key[j] + '}');
                                inner_template = inner_template_list.join(', ');
                                inner_mapping[text_key[j]] = 'test';
                                inner_mapping[text_key[j]] = data[i][text_key[j]] || 'none';
                                j += 1;
                            }
                            option_text = MAG.TEMPLATE.substitute(inner_template, inner_mapping);
                        }
                        //final mapping object for option
                        mapping = {val: data[i][value_key] || data[i], text: option_text || data[i][text_key] || data[i] || ' ', select: ""};
                        if (typeof selected_option_value !== 'undefined' && (data[i][value_key] === selected_option_value || data[i] === selected_option_value || data[i] === String(selected_option_value))) {
                            mapping.select = ' selected="selected"';
                        }
                        options += MAG.TEMPLATE.substitute(template, mapping);
                    }
                    select.innerHTML = options;
                },


                get_value: function (elem) {
                    var value;
                    value = null;
                    if ((elem.tagName === 'INPUT' && (elem.type !== 'checkbox' && elem.type !== 'radio')) || elem.tagName === 'TEXTAREA') {
                        if (elem.value !== '') {
                            value = elem.value;
                            if (MAG.ELEMENT.has_className(elem, 'stringlist')) {
                                value = value.split('|');
                            } else {
                                if (MAG.ELEMENT.has_className(elem, 'integer')) {
                                    value = parseInt(value, 10);
                                } else if (MAG.ELEMENT.has_className(elem, 'datetime')) {
                                    value = {'$date': parseInt(value)};
                                }
                            }
                        }
                    } else {
                        if (elem.type === 'checkbox') {
                            if (MAG.ELEMENT.has_className(elem, 'boolean')) {
                                if (elem.checked) {
                                    value = true;
                                } else {
                                    value = null;
                                }
                            } else {
                                if (elem.checked) {
                                    value = elem.value;
                                }
                            }
                        } else {
                            if (elem.tagName === 'SELECT') {
                                value = elem.value;
                                if (value !== 'none') {
                                    if (MAG.ELEMENT.has_className(elem, 'integer')) {
                                        value = parseInt(value, 10);
                                    } else {
                                        if (MAG.ELEMENT.has_className(elem, 'boolean')) {
                                            if (value === 'true') {
                                                value = true;
                                            } else {
                                                if (value === 'false') {
                                                    value = false;
                                                }
                                            }
                                        }
                                    }
                                } else {
                                    value = null;
                                }
                            } else {
                                if (elem.type === 'radio') {
                                    if (elem.checked  === true) {
                                        value = elem.value;
                                    }
                                }     
                            }
                        } 
                    }
                    return value;
                },

                /**TODO: make sure you catch errors with parseInt and leave
                   the string as it is - forms should be validating entry
                   anyway before this point! */
                serialize_form: function (form_id, elem_list, prefix) {
                    var i, j, k, elems, json, elem, value, subelems, key, subjson;
                    if (elem_list === undefined) {
                        elems = document.getElementById(form_id).elements;
                    } else {
                        elems = elem_list;
                    }
                    json = {};
                    for (i = 0; i < elems.length; i += 1) {
                        elem = elems[i];
                        value = null;
                        if (elem.disabled === false){     
                            if (elem.name ||  MAG.ELEMENT.has_className(elem, 'data_group')) {
                                if (MAG.ELEMENT.has_className(elem, 'data_group')) {
                                    /** construct a list of all elements
                                        descending from elem */
                                    subelems = [];
                                    j = i + 1;
                                    while (MAG.ELEMENT.is_ancestor(elems[j], elem)) {
                                        subelems.push(elems[j]);
                                        j += 1;
                                    }
                                    if (prefix === undefined) {
                                        key = elem.id;
                                    } else {
                                        key = elem.id.replace(prefix, '');
                                    }
                                    subjson = MAG.FORMS.serialize_form(form_id, subelems, elem.id + '_');
                                    console.log(subjson)
                                    if (!MAG.TYPES.is_empty_object(subjson)) {
                                        if (MAG.ELEMENT.has_className(elem, 'objectlist')) {
                                            try {
                                                json[key.substring(0, key.lastIndexOf('_'))].push(subjson);
                                            } catch (err) {
                                                json[key.substring(0, key.lastIndexOf('_'))] = [subjson];
                                            }
                                        } else if (MAG.ELEMENT.has_className(elem, 'stringlist')) {
                                            json[key] = [];
                                            for (k in subjson) {
                                                if (subjson.hasOwnProperty(k)) {
                                                    json[key].push(subjson[k]);
                                                }
                                            }
                                        } else {
                                            json[key] = subjson;
                                        }
                                    }
                                    i = j - 1;
                                } else {
                                    value = MAG.FORMS.get_value(elem);
                                    if (value !== null) {
                                        if (prefix === undefined) {
                                            json[elem.name] = value;
                                        } else {
                                            json[elem.name.replace(prefix, '')] = value;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    return json;
                },

                /** populates the provided field with the provided data */
                populate_field: function (field, data) {
                    var i;
                    if (
                        (field.tagName === 'INPUT' &&
                         field.type !== 'checkbox') ||
                            field.tagName === 'TEXTAREA'
                    ) {
                        if (MAG.TYPES.is_array(data)) {
                            field.value = data.join('|');
                        } else {
                            field.value = data;
                        }
                    } else if (field.type === 'checkbox') {
                        field.checked = data;
                    } else if (field.tagName === 'SELECT') {
                        if (MAG.TYPES.is_number(data)) {
                            data = data.toString();
                        }
                        if (field.options.length > 0) {
                            for (i = 0; i < field.options.length; i += 1) {
                                if (field.options[i].value === data) {
                                    field.options[i].selected = true;
                                }
                            }
                        }
                    }
                    return;
                },

                /** Populate a simple form from a JSON object
                    A simple form is defined as one which has all
                    fields visible at all times
                    perhaps better called static?
                    requires id on elements to be the same as the
                    corresponding JSON key
                    Embedded objects should have all keys in their
                    ancestor tree joined with '_'
                    inputs:
                    data: the JSON object
                    form: the form object to populate
                    prefix: used internally for dealing with embedded data*/
                populate_simple_form: function (data, form, prefix) {
                    var field, key;
                    if (prefix === undefined) {
                        prefix = '';
                    }
                    for (key in data) {
                        if (data.hasOwnProperty(key)) {
                            if (MAG.TYPES.is_object(data[key])) {
                                MAG.FORMS.populate_simple_form(data[key], form, prefix + key + '_');
                            } else if (MAG.TYPES.is_array(data[key]) &&
                                       MAG.TYPES.is_object(data[key][0])) {
                                MAG.FORMS.populate_simple_form(data[key], form, prefix + key + '_');
                            } else {
                                field = document.getElementById(prefix + key);
                                if (field) {
                                    MAG.FORMS.populate_field(field, data[key]);
                                }
                            }
                        }
                    }
                },

                /** Populate a HTML form from a JSON object
                    complex is defined as a form which alows users to
                    manipulate the fields on display (adding extra rows etc.)
                    this function will attempt to use the add functions to
                    add the fields required to represent the JSON
                    NB if adding fields fails data will be lost so this must be
                    tested well for each form it is used for
                    and the form structure and javascript function names
                    manipulated as necessary to acheive desired behaviour
                    requires id on elements to be the same as the corresponding
                    JSON key
                    Embedded objects should have all keys in their ancestor tree
                    joined with '_'
                    the function for adding new fields should be 'add_' plus the
                    name of the fieldset being added minus the number count
                    inputs:
                    data: the JSON object
                    form: the form object to populate
                    js_namespace: the namespace string in which the
                    functions for
                    adding extra fields live (all must be in the same one)
                    prefix_list: used internally for dealing with embedded
                    data*/
                populate_complex_form: function (data, form, js_name_space, prefix_list) {
                    //assumes ids are the same as json key
                    var field, key, i, fnstring;
                    if (prefix_list === undefined) {
                        prefix_list = [];
                    }
                    for (key in data) {
                        if (data.hasOwnProperty(key)) {
                            if (MAG.TYPES.is_object(data[key])) {
                                prefix_list.push(key);
                                MAG.FORMS.populate_complex_form(data[key], form, js_name_space, prefix_list);
                                //objectlist
                            } else if (MAG.TYPES.is_array(data[key]) && MAG.TYPES.is_object(data[key][0])) {
                                prefix_list.push(key);
                                MAG.FORMS.populate_complex_form(data[key], form, js_name_space, prefix_list);
                            } else {
                                if (prefix_list.length > 0) {
                                    field = document.getElementById(prefix_list.join('_') +  '_' +  key);
                                } else {
                                    field = document.getElementById(key);
                                }
                                if (field) {
                                    MAG.FORMS.populate_field(field, data[key]);
                                } else {
                                    i = 1;
                                    while (field === null && i <= prefix_list.length) {
                                        fnstring = js_name_space + '.add_' + prefix_list.slice(0, i * -1).join('_');
                                        try {
                                            MAG.FUNCTOOLS.get_function_from_string(fnstring)();
                                            field = document.getElementById(prefix_list.join('_') + '_' + key);
                                            MAG.FORMS.populate_field(field,data[key]);
                                        } catch (err) {
                                            //ignore
                                        }
                                        i += 1;
                                    }
                                }
                            }
                        }
                    }
                    if (prefix_list.length > 0) {
                        prefix_list.pop();
                    }
                    return;
                },


                /** Options
                    next:
                    success: callback function called on success.
                 */
                submit: function (form_id, options) {
                    var validation;
                    validation = MAG.FORMS.validate_form(form_id);
                    if (validation.result === true) {
                        MAG.FORMS.save(form_id, options);
                    } else {
                        MAG.DISPLAY.show_validation(validation);
                        MAG.FORMS.show_error_box('<br/>The data is not valid and cannot be saved. Please fix the errors and resave.'
                                                   + '<br/><br/>Red label text indicates that required data has not been supplied.'
                                                   + '<br/>A red background indicates that the data in that box is not in a format that is valid.');
                    }
                    return;
                },

                save: function (form_id, options) {
                    if (typeof options == "undefined") {
                        options = {};
                    }
                    options.json = MAG.FORMS.serialize_form(form_id);
                    options.model = options.json._model
                    if (options.json.hasOwnProperty('_id')) {
                        options.type = 'update';
                    } else {
                        options.type = 'create';
                    }
                    return MAG.FORMS.save_resource(form_id, options);
                },

                save_resource: function (form_id, options) {
                    var newoptions, item;
                    newoptions = {'success': function(response) {
                        for (item in localStorage) {
                            if (item.indexOf('/api/' + form_id.replace('_form', '')) !== -1) {
                                delete localStorage[item];
                            }
                        }
                        if (typeof options.success != "undefined") {
                            options.success(response, options);
                        } else {
                            MAG.FORMS.reloader(response, options);
                        }
                    }, 'error': function(response) {
                        MAG.FORMS.handle_error('create', response, options.json._model);
                    }};
                    if (options.type === 'create') {
                        MAG.REST.create_resource(options.json._model, options.json, newoptions);
                    } else if (options.type === 'update') {
                        MAG.REST.update_resource(options.json._model, options.json, newoptions);
                    }
                },

                reloader: function(response, options) {
                    if (options.next === undefined) {
                        window.location.search = response._model + '=' + response._id;
                    } else {
                        window.location = options.next;
                    }
                },

                show_error_box: function (report) {
                    var error_div;
                    if (document.getElementById('error') !== null) {
                        document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
                    }
                    error_div = document.createElement('div');
                    error_div.setAttribute('id', 'error');
                    error_div.setAttribute('class', 'error_message');
                    error_div.innerHTML = '<span id="error_title"><b>Error</b></span><div id="error_close">close</div><br/><br/>' + report;
                    document.getElementsByTagName('body')[0].appendChild(error_div);
                    MAG.EVENT.addEventListener(document.getElementById('error_close'), 'click', function(event){
                        document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
                    });
                },


                handle_error: function (action, error_report, model) {
                    var report;
                    report = 'An error has occurred.<br/>';
                    if (error_report.status === 401) {
                        report += '<br/>You are not authorised to ' + action + ' an entry in the ' + model + ' table.';
                    } else if (error_report.status === 409) {
                        report += '<br/>It is not possible to ' + action + ' this ' + model + ' because an entry already exists with the same id.';
                    } else if (error_report.status === 404) {
                        report += '<br/>It is not possible to ' + action + ' this ' + model + ' because there is no ' + model + ' with this id.';
                        report += '<br/><br/>This form can be used to add a new ' + model + '.';
                    } else {
                        report += '<br/>The server has encountered an error. Please try again. <br/>If the problem persists please contact the server administrator.';
                    }
                    MAG.FORMS.show_error_box(report);
                }



                // End of submodule FORMS
            };
        }()),

        DISPLAY: (function () {

            return {
                hello: function () {
                    console.log('display');
                },
                /**************************************************
                 * Single Instance Stuff
                 */

                /* Show a single instance in a table
                 * options are
                 *    key_order (supplied one will overwrite any others)
                 *    show_blanks
                 *    */
                show_instance_table: function (json, container_id, options) {
                    var container, html, show_blanks;
                    container = document.getElementById(container_id) || document.getElementsByTagName('body')[0];
                    html = [];
                    show_blanks = options.blanks || false;
                    if (options !== undefined && options.key_order !== undefined) {
                        html = MAG.DISPLAY.create_instance_table(json, options.key_order, show_blanks);
                        container.innerHTML = '<table class="data_instance">' + html.join('') + '</table>';
                    } else if (json.hasOwnProperty('_view') && json._view.hasOwnProperty('instance')) {
                        html = MAG.DISPLAY.create_instance_table(json, json._view.instance, show_blanks);
                        container.innerHTML = '<table class="data_instance">' + html.join('') + '</table>';
                    } else {
                        MAG.REST.apply_to_resource('_model', json._model, {'success' : function (response) {
                            if (response.hasOwnProperty('_view') && response._view.hasOwnProperty('instance')) {
                                html = MAG.DISPLAY.create_instance_table(json, response._view.instance, show_blanks);
                                container.innerHTML = '<table class="data_instance">' + html.join('') + '</table>';
                            }
                        }});
                    }
                },

                create_instance_table: function(json, key_order, show_blanks, level) {
                    var html, i, j, label, key;
                    if (level === undefined) {
                        level = 0;
                    }
                    html = [];
                    for (i = 0; i < key_order.length; i += 1) {
                        if (MAG.TYPES.is_string(key_order[i])) {
                            key = key_order[i];
                            label = MAG.DISPLAY.capitalise_titles(key.replace(/_/g, ' '));
                        } else if (MAG.TYPES.is_object(key_order[i])) {
                            key = key_order[i].id;
                            label = key_order[i].label || MAG.DISPLAY.capitalise_titles(key.replace(/_/g, ' '));
                        }
                        if (json.hasOwnProperty(key)) {
                            html.push('<tr>');
                            if (MAG.TYPES.is_string(json[key]) || MAG.TYPES.is_number(json[key])) {
                                html.push('<td class="label level' + level + '">' + label + '</td>');
                                html.push('<td class="data level' + level + '">' + json[key] + '</td>');
                            } else if (MAG.TYPES.is_boolean(json[key])) {
                                html.push('<td class="label level' + level + '">' + label + '</td>');
                                if (json[key] === true) {
                                    html.push('<td class="data level' + level + '">Y</td>');
                                } else {
                                    html.push('<td class="data level' + level + '">N</td>');
                                }
                            } else if (MAG.TYPES.is_array(json[key])) {
                                if (MAG.TYPES.is_object(json[key][0])) {
                                    html.push('<td class="label level' + level + '">' + label + '</td>');
                                    html.push('<td class="data level' + level + '">' );
                                    html.push('<table class="inner">');
                                    html = html.concat(MAG.DISPLAY.create_instance_list_table(json[key], key_order[i].instance));
                                    html.push('</table>');
                                    html.push('</td>');
                                } else {
                                    html.push('<td class="label level' + level + '">' + label + '</td>');
                                    html.push('<td class="data level' + level + '">' );
                                    for (j=0; j<json[key].length; j+=1) {
                                        html.push(json[key][j]);
                                        html.push('<br/>')
                                    }
                                    html.push('</td>');
                                }
                            } else if (MAG.TYPES.is_object(json[key])) {
                                if (key_order[i].hasOwnProperty('instance')) {
                                    html.push('<td class="label container level' + level + '">' + label + '</td>');
                                    html.push('<td class="data container level' + level + '"></td>');
                                    html = html.concat(MAG.DISPLAY.create_instance_table(json[key], key_order[i].instance, show_blanks, level += 1));
                                    level = level-1;
                                } else {
                                    html.push('<td class="label level' + level + '">' + label + '</td>');
                                    //process as dictionary
                                    html.push('<td class="data">');
                                    html.push(MAG.DISPLAY.format_dictionary(json[key]));
                                    html.push('</td>');
                                }
                            } else {
                                html.push('<td class="label level' + level + '">' + label + '</td>');
                                html.push('<td class="data level' + level + '">' + json[key] + '</td>');
                            }
                            html.push('</tr>');
                        } else if (show_blanks === true) {
                            html.push('<tr>');
                            html.push('<td class="label level' + level + '">' + label + '</span>');
                            html.push('<td class="data level' + level + '"></span>');
                            html.push('</tr>');
                        }
                    }
                    return html;
                },

                /**************************************************
                 * List Display Stuff
                 */

                /* Show a list of instances in a table
                 * options are
                 * key_order: list of keys (supplied one will overwrite the one in the model)
                 * auto_filter: boolean to say whether or not to attempt to provide automatic sorting on fields
                 * preprocess: provide a preprocessing callback
                 *
                 */
                //TODO: add a default sort to the info in citation_models and use it here
                show_instance_list_table: function (model, container_id, options) {
                    var container, html, key, key_list, auto_sort, param_dict,
                        page_num, page_size, search, criteria, sort, filter_key,
                        callback;
                    container = document.getElementById(container_id) || document.getElementsByTagName('body')[0];
                    html = [];
                    //supplied options
                    if (typeof options === 'undefined') {
                        options = {};
                    }
                    if (options.hasOwnProperty('auto_sort')) {
                        auto_sort = options.auto_sort;
                    } else {
                        auto_sort = false;
                    }
                    if (options.hasOwnProperty('page_size')) {
                        if (options.page_size === 'all') {
                            page_size = null;
                        } else {
                            page_size = options.page_size;
                        }
                    } else {
                        page_size = null;
                    }
                    //url data
                    param_dict = MAG.URL.get_current_query();
                    if (param_dict.hasOwnProperty('page')){
                        page_num = param_dict.page;
                    } else {
                        page_num = 1;
                    }
                    delete param_dict['page'];
                    if (param_dict.hasOwnProperty('sort')) {
                        sort = param_dict.sort;
                    } else {
                        sort = null;
                    }
                    delete param_dict['sort'];
                    if (param_dict.hasOwnProperty('size')) {
                        page_size = param_dict.size;
                    } //already set to null above (or to supplied value)
                    delete param_dict['size'];
                    MAG.REST.apply_to_resource('_model', model, {'success' : function (model_json) {
                        if (model_json.hasOwnProperty('_view')
                            && model_json._view.hasOwnProperty('list')
                            && model_json._view.list.hasOwnProperty('read')) {
                            key_list = model_json._view.list.read;
                            MAG.AUTH.check_permission(model, 'update', {'success': function (update_permission){
                                if (update_permission === true) {
                                    if (model_json.hasOwnProperty('_view')
                                        && model_json._view.hasOwnProperty('list')
                                        && model_json._view.list.hasOwnProperty('update')){
                                        key_list = model_json._view.list.update;
                                    }
                                }
                                //TODO:need to sort this out with getting other info required from model once the rest works!!!
                                if (options.hasOwnProperty('key_order')) {
                                    console.log('key order supplied - needs fixing')
                                    html = MAG.DISPLAY.create_instance_list_table(json, options.key_order);
                                    container.innerHTML = '<table class="data_list">' + html.join('') + '</table>';
                                } else {
                                    criteria = {'_count':'true'};
                                    if (page_size !== null) {
                                        criteria['_limit'] = 'JSON:' + page_size;
                                        criteria['_skip'] = 'JSON:' + (page_num-1)*page_size;
                                    }
                                    for (key in param_dict) {
                                        if (param_dict.hasOwnProperty(key)) {
                                            criteria[key] = param_dict[key];
                                        }
                                    }
                                    if (sort !== null) {
                                        criteria['_sort'] = [[sort.split('|')[0], parseInt(sort.split('|')[1])]];
                                    } else {
                                        if (typeof model_json._view.sort !== 'undefined'){
                                            criteria['_sort'] = [[model_json._view.sort, 1]];
                                        } else {
                                            criteria['_sort'] = [['_id', 1]];
                                        }
                                    }
                                    MAG.REST.apply_to_list_of_resources(model, {'criteria' : criteria, 'force_reload': true, 'success' : function (json) {
                                        callback = function(data) {
                                            MAG.DISPLAY.populate_show_instance_list_table(
                                                data, key_list, auto_sort, criteria,
                                                html, container, model, page_num,
                                                param_dict, model_json, page_size,
                                                filter_key);
                                        }

                                        if (typeof options.preprocess != "undefined") {
                                            options.preprocess(json, callback);
                                        } else {
                                            callback(json);
                                        }

                                    }});
                                }
                            }});
                        } else {
                            alert('no order list for ' + model);
                        }
                    }});
                },

                populate_show_instance_list_table: function(
                    data, key_list, auto_sort, criteria, html,
                    container, model, page_num, param_dict, model_json,
                    page_size, filter_key) {
                    var key;
                    if (data.results.length > 0) {
                        html = MAG.DISPLAY.create_instance_list_table(
                            data.results, key_list, auto_sort,
                            criteria._sort[0] || undefined);
                        container.innerHTML = '<table class="data_list">' + html + '</table>';
                        if (auto_sort === true) {
                            MAG.DISPLAY.add_sort_handlers(key_list);
                        }
                        if (document.getElementById('page_title') !== null) {
                            document.getElementById('page_title').innerHTML = MAG.DISPLAY.capitalise_titles(model) + ' List';
                        }
                        if (document.getElementById('page_nav') !== null) {
                            if (document.getElementById('page_size') !== null) {
                                document.getElementById('page_size').innerHTML = '<select id="page_size_select"></select> per page';
                                MAG.FORMS.populate_select(['20', '50', '100', 'all'], document.getElementById('page_size_select'), undefined, undefined, page_size);
                                MAG.EVENT.addEventListener(document.getElementById('page_size_select'), 'change', function(event){
                                    window.location = '?' + MAG.DISPLAY.create_new_query({'size': (parseInt(event.target.value))});
                                });
                            }
                            MAG.DISPLAY.get_navigation_widget(document.getElementById('page_nav'), data.count, page_num, page_size, {'buttons': true, 'angle_brackets': true});
                        }
                        if (document.getElementById('search_widget') !== null) {
                            for (key in param_dict) {
                                if (key !== 'page' && param_dict.hasOwnProperty(key)) {
                                    filter_key = key;
                                }
                            }
                            if (typeof filter_key !== 'undefined') {
                                MAG.DISPLAY.create_search_widget(model, model_json, filter_key);
                            } else {
                                MAG.DISPLAY.create_search_widget(model, model_json);
                            }
                        }
                    } else {
                        document.getElementById('content').innerHTML = '<br/><br/>There are no entries in the database to view.';
                    }
                },

                create_search_widget: function (model, model_json, filter_key) {
                    var search_field, search_text, search_query, remove_filter;
                    if (typeof filter_key !== 'undefined') {
                        remove_filter = '<input id="remove" type="button" value="remove ' + MAG.DISPLAY.capitalise_titles(filter_key.replace(/_/g, ' ')) +  ' filter"/>';
                    } else {
                        remove_filter = '';
                    }
                    document.getElementById('search_widget').innerHTML = '<select id="search_field"></select><input type="text" id="search_text"/><input id="search" type="button" value="Go"/>' + remove_filter;
                    MAG.DISPLAY.get_search_widget(document.getElementById('search_widget'), model);
                    if (document.getElementById('remove') !== null) {
                        MAG.EVENT.addEventListener(document.getElementById('remove'), 'click', function(){
                            window.location = window.location.href.split('?')[0];
                        });
                    }
                    MAG.EVENT.addEventListener(document.getElementById('search'), 'click', function(){
                        search_field = document.getElementById('search_field');
                        search_text = document.getElementById('search_text');
                        search_query = {};
                        if (search_field !== null && search_text !== null && search_field.value !== 'none' && search_text.value !== '') {
                            if (model_json[search_field.value].field === 'Boolean') {
                                if (search_text.value === 'Y') {
                                    search_query[search_field.value] = 'JSON:true';
                                } else {
                                    search_query[search_field.value] = 'JSON:' + encodeURIComponent(JSON.stringify({'$exists': false}));
                                }
                            } else if (model_json[search_field.value].field !== 'Char' && model_json[search_field.value].field !== 'Text') {
                                search_query[search_field.value] = 'JSON:' + search_text.value;
                            } else {
                                search_query[search_field.value] = search_text.value;
                            }
                            document.location.search = '?' + MAG.DISPLAY.create_new_query(search_query, ['sort']);
                        }
                    });
                },

                get_search_widget: function(container, model) {
                    var i, key_list, key_json, json_list;
                    key_json = {};
                    json_list = [];
                    if (container !== null || container !== undefined) {
                        MAG.REST.apply_to_resource('_model', model, {'success' : function (response) {
                            MAG.AUTH.check_permission(model, 'read', {'success': function (read_permission) {
                                if (read_permission === true) {
                                    if (response.hasOwnProperty('_view')
                                        && response._view.hasOwnProperty('list')
                                        && response._view.list.hasOwnProperty('read')) {
                                        key_list = response._view.list.read;
                                    }
                                }
                                MAG.AUTH.check_permission(model, 'update', {'success': function (update_permission) {
                                    if (update_permission === true) {
                                        if (response.hasOwnProperty('_view')
                                            && response._view.hasOwnProperty('list')
                                            && response._view.list.hasOwnProperty('update')) {
                                            key_list = response._view.list.update;
                                        }
                                    }
                                    for (i = 0; i < key_list.length; i += 1) {
                                        if (MAG.TYPES.is_string(key_list[i])) {
                                            key_json['field'] = key_list[i];
                                            key_json['string'] = MAG.DISPLAY.capitalise_titles(key_list[i].replace(/_/g, ' '));
                                            json_list.push(key_json);
                                            key_json = {};
                                        } else if (MAG.TYPES.is_object(key_list[i])
                                                   && !key_list[i].hasOwnProperty('type')
                                                   && key_list[i].hasOwnProperty('id')) {
                                            key_json['field'] = key_list[i].id;
                                            key_json['string'] = key_list[i].label || MAG.DISPLAY.capitalise_titles(key_list[i].id.replace(/_/g, ' '));
                                            json_list.push(key_json);
                                            key_json = {};
                                        }
                                    }
                                    MAG.FORMS.populate_select(json_list, document.getElementById('search_field'), 'field', 'string');
                                }});
                            }});
                        }});
                    }
                },

                sort_table: function(id) {
                    var new_args, index, direction;
                    index = id.lastIndexOf('_');
                    if (id.substring(index+1) === 'up') {
                        direction = 1;
                    } else if (id.substring(index+1) === 'down') {
                        direction = -1;
                    }
                    new_args = {'sort': id.substring(0, index) + '|' + direction};
                    window.location = '?' + MAG.DISPLAY.create_new_query(new_args);
                },

                add_sort_handlers: function(key_order) {
                    var i;
                    for (i = 0; i < key_order.length; i += 1) {
                        if (MAG.TYPES.is_object(key_order[i])) {
                            if (!key_order[i].hasOwnProperty('type')){
                                if (document.getElementById(key_order[i].id + '_up') !== null) {
                                    MAG.EVENT.addEventListener(document.getElementById(key_order[i].id + '_up'), 'click', function (event){
                                        MAG.DISPLAY.sort_table(event.target.id);
                                    });
                                    MAG.EVENT.addEventListener(document.getElementById(key_order[i].id + '_down'), 'click', function (event){
                                        MAG.DISPLAY.sort_table(event.target.id);
                                    });
                                }
                            }
                        } else {
                            if (document.getElementById(key_order[i] + '_up') !== null) {
                                MAG.EVENT.addEventListener(document.getElementById(key_order[i] + '_up'), 'click', function (event){
                                    MAG.DISPLAY.sort_table(event.target.id);
                                });
                                MAG.EVENT.addEventListener(document.getElementById(key_order[i] + '_down'), 'click', function (event){
                                    MAG.DISPLAY.sort_table(event.target.id);
                                });
                            }
                        }
                    }
                },

                create_instance_list_table: function (json, key_order, auto_sort, sort) {
                    var rows, header, i;
                    rows = [];
                    header = [];
                    /* header */
                    header = MAG.DISPLAY.get_list_instance_header(key_order, header, auto_sort, sort);
                    /* data */
                    for (i = 0; i < json.length; i += 1) {
                        if (rows.length % 2 === 1) {
                            rows.push('<tr class="odd">' + MAG.DISPLAY.get_list_instance_data(json[i], key_order) + '</tr>');
                        } else {
                            rows.push('<tr>' + MAG.DISPLAY.get_list_instance_data(json[i], key_order) + '</tr>');
                        }
                    }
                    return '<tr class="header">' + header.join('') + '</tr>' + rows.join('');
                },

                get_sort_links: function (key, direction) {
                    if (direction === 1) {
                        return '<div class="sort_links"><span id="' + key + '_up">&#9650;</span><span id="' + key + '_down">&#9663;</span></div>';
                    } else if (direction === -1) {
                        return '<div class="sort_links"><span id="' + key + '_up">&#9653;</span><span id="' + key + '_down">&#9660;</span></div>';
                    } else {
                        return '<div class="sort_links"><span id="' + key + '_up">&#9653;</span><span id="' + key + '_down">&#9663;</span></div>';
                    }
                },

                get_list_instance_header: function (key_order, header, auto_sort, sort) {
                    var i, label;
                    for (i = 0; i < key_order.length; i += 1) {
                        if (MAG.TYPES.is_string(key_order[i])) {
                            header.push('<th><div class="field_header">' + MAG.DISPLAY.capitalise_titles(key_order[i].replace(/_/g, ' ')) + '</div>');
                            if (auto_sort === true) {
                                if (key_order[i] === sort[0]) {
                                    header.push(MAG.DISPLAY.get_sort_links(key_order[i], sort[1]));
                                } else {
                                    header.push(MAG.DISPLAY.get_sort_links(key_order[i]));
                                }
                            }
                            header.push('</th>');
                        } else if (MAG.TYPES.is_object(key_order[i])) {
                            if (key_order[i].hasOwnProperty('instance')) {
                                label = key_order[i].label || key_order[i].id || '';
                                header.push('<th class="container"><table class="inner"><tbody>');
                                header.push('<tr><th colspan="' + key_order[i].instance.length + '">' + MAG.DISPLAY.capitalise_titles(label.replace(/_/g, ' ')) + '</th></tr>');
                                header.push('<tr>');
                                header = MAG.DISPLAY.get_list_instance_header(key_order[i].instance, header);
                                header.push('</tr>');
                                header.push('</tbody></table></th>');
                            } else if (key_order[i].hasOwnProperty('label')) {
                                header.push('<th><div class="field_header">' + MAG.DISPLAY.capitalise_titles(key_order[i].label.replace(/_/g, ' ')) + '</div>')
                                if (auto_sort === true) {
                                    if (key_order[i].id === sort[0]) {
                                        header.push(MAG.DISPLAY.get_sort_links(key_order[i].id, sort[1]));
                                    } else {
                                        header.push(MAG.DISPLAY.get_sort_links(key_order[i].id));
                                    }
                                }
                                header.push('</th>');
                            } else if (key_order[i].hasOwnProperty('id')) {
                                header.push('<th><div class="field_header">' + MAG.DISPLAY.capitalise_titles(key_order[i].id.replace(/_/g, ' ')) + '</div>');
                                if (auto_sort === true) {
                                    if (key_order[i].id === sort[0]) {
                                        header.push(MAG.DISPLAY.get_sort_links(key_order[i].id, sort[1]));
                                    } else {
                                        header.push(MAG.DISPLAY.get_sort_links(key_order[i].id));
                                    }
                                }
                                header.push('</th>');
                            } else {
                                header.push('<th></th>');
                            }
                        }
                    }
                    return header;
                },

                get_list_instance_data: function (json, key_order) {
                    var i, j, cells, param_string, param_list, entry, key;
                    param_string = '';
                    cells = [];
                    for (i = 0; i < key_order.length; i += 1) {
                        if (MAG.TYPES.is_object(key_order[i])
                            && key_order[i].hasOwnProperty('type')
                            && key_order[i].type === 'link') {
                            if (!key_order[i].hasOwnProperty('href')) {
                                // we can't have a link without a href - return empty cell
                                cells.push('<td></td>');
                            } else {
                                param_string = '';
                                param_list = [];
                                param_string += '?';
                                //in here check if back is True
                                if (key_order[i].hasOwnProperty('back') && key_order[i].back === true) {
                                    param_list.push('back=' + encodeURIComponent(window.location));
                                }
                                //if it is then catch the current url and add it to param list
                                //need to move param list further out of the loop for this to work
                                if (key_order[i].hasOwnProperty('params')) {
                                    for (entry in key_order[i].params) {
                                        if (key_order[i].params.hasOwnProperty(entry)) {
                                            if (key_order[i].params[entry].indexOf('VAR-') !== -1) {
                                                param_list.push(entry + '=' + json[key_order[i].params[entry].replace('VAR-', '')]);
                                            } else {
                                                param_list.push(entry + '=' + key_order[i].params[entry]);
                                            }
                                        }
                                    }
                                }
                                param_string += (param_list.join('&'));
                                cells.push('<td><a href="' + key_order[i].href + param_string + '">' + key_order[i].text + '</a></td>');
                            }
                        } else {
                            if (MAG.TYPES.is_string(key_order[i])) {
                                key = key_order[i];
                            } else if (MAG.TYPES.is_object(key_order[i])) {
                                key = key_order[i].id;
                            }
                            if (json.hasOwnProperty(key)) {
                                if (MAG.TYPES.is_string(json[key]) || MAG.TYPES.is_number(json[key])) {
                                    cells.push('<td class="data">' + json[key] + '</td>');
                                } else if (MAG.TYPES.is_boolean(json[key])) {
                                    if (json[key] === true) {
                                        cells.push('<td class="data">Y</td>');
                                    } else {
                                        cells.push('<td class="data">N</td>');
                                    }
                                } else if (MAG.TYPES.is_object(json[key])) {
                                    if (key_order[i].hasOwnProperty('instance')) {
                                        cells.push('<td class="container"><table class="inner"><tbody>');
                                        cells.push('<tr>');
                                        cells = cells.concat(MAG.DISPLAY. get_list_instance_data(json[key], key_order[i].instance));
                                        cells.push('</tr>');
                                        cells.push('</tbody></table></td>');
                                    } else {
                                        //process as dictionary
                                        cells.push('<td>');
                                        cells.push(MAG.DISPLAY.format_dictionary(json[key]));
                                        cells.push('</td>');
                                    }
                                } else if (MAG.TYPES.is_array(json[key])) {
                                    cells.push('<td class="container"><table class="inner"><tbody>');
                                    for (j = 0; j < json[key].length; j += 1) {
                                        cells.push('<tr>');
                                        cells = cells.concat(MAG.DISPLAY. get_list_instance_data(json[key][j], key_order[i].instance));
                                        cells.push('</tr>');
                                    }
                                    cells.push('</tbody></table></td>');
                                } else {
                                    cells.push('<td class="data"></td>');
                                }
                            } else {
                                cells.push('<td class="data"></td>');
                            }
                        }
                    }
                    return cells.join('');
                },

                /* creates a new query dictionary from the current query (in the url)
                 * and the query dictionary supplied as the first argument to the function.
                 * If no second argument is provided then all fields from the current dict and the
                 * supplied dict are merged with the values from the supplied dict taking priority
                 * If the optional list of preserve_fields is supplied then only the keys in this list
                 * are preserved from the original query and then any new fields are added from the supplied
                 * query (values from the supplied query are again prioritised over the originals
                 */
                create_new_query: function (new_args, preserve_fields) {
                    var current_args, key, i, query_list;
                    current_args = MAG.URL.get_current_query();
                    query_list = [];
                    if (typeof preserve_fields === 'undefined') {
                        //keep everything but change the values of args in new args or just add them to existing
                        for (key in new_args) {
                            if (new_args.hasOwnProperty(key)) {
                                current_args[key] = new_args[key];
                            }
                        }
                        for (key in current_args) {
                            if (current_args.hasOwnProperty(key)) {
                                query_list.push(key + '=' + current_args[key])
                            }
                        }
                        return MAG.URL.build_query_string(current_args);
                    } else {
                        // keep the things in the preserve_fields list and remove everything else
                        for (i = 0; i < preserve_fields.length; i += 1) {
                            if (current_args.hasOwnProperty(preserve_fields[i])) {
                                if (!new_args.hasOwnProperty(preserve_fields[i])) {
                                    new_args[preserve_fields[i]] = current_args[preserve_fields[i]];
                                }
                            }
                        }
                        for (key in new_args) {
                            if (new_args.hasOwnProperty(key)) {
                                query_list.push(key + '=' + new_args[key])
                            }
                        }
                        return query_list.join(';');
                    }
                },

                format_dictionary: function (json) {
                    var key, cells;
                    cells = [];
                    for (key in json) {
                        if (key !== '_model' && json.hasOwnProperty(key)) {
                            cells.push(MAG.DISPLAY.capitalise_titles(key.replace(/_/g, ' ')));
                            cells.push(' = ');
                            cells.push(json[key]);
                            cells.push('<br/>');
                        }
                    }
                    return cells.join('');
                },

                show_validation: function(validation_data) {
                    var i;
                    if (validation_data.result === false) {
                        for (i = 0; i < validation_data.missing.length; i += 1) {
                            MAG.ELEMENT.add_className(document.getElementById(validation_data.missing[i]).parentNode, 'missing');
                        }
                        for (i = 0; i < validation_data.invalid.length; i += 1) {
                            MAG.ELEMENT.add_className(document.getElementById(validation_data.invalid[i]), 'error');
                        }
                    }
                    return;
                },

                capitalise_titles: function(text) {
                    var glue, j;
                    glue = ['of', 'for', 'and', 'in', 'to'];
                    return text.replace(/(\w)(\w*)/g, function(_, i, r) {
                        j = i.toUpperCase() + (r != null ? r : "");
                        return (glue.indexOf(j.toLowerCase())<0)?j:j.toLowerCase();
                    });
                },

                get_navigation_widget: function (container, total_records, page_number, page_size, display_options) {
                    var previous_string, next_string, total_pages, first_page, last_page, select_string, option_string, i, buttons;
                    var previous_text, first_text, next_text, last_text;
                    var previous_text_disabled, first_text_disabled, next_text_disabled, last_text_disabled;
                    buttons = false;
                    previous_text = 'previous';
                    first_text = 'first';
                    next_text = 'next';
                    last_text = 'last';
                    if (display_options !== undefined) {
                        if (display_options.angle_brackets && display_options.angle_brackets === true) {
                            previous_text = '&lt;';
                            first_text = '&lt;&lt;';
                            next_text = '&gt;';
                            last_text = '&gt;&gt;';
                        }
                        if (display_options.buttons && display_options.buttons === true) {
                            previous_text_disabled = '<button class="linkbutton" type="button" disabled="disabled">' + previous_text + '</button>';
                            first_text_disabled = '<button class="linkbutton" type="button" disabled="disabled">' + first_text + '</button>';
                            next_text_disabled = '<button class="linkbutton" type="button" disabled="disabled">' + next_text + '</button>';
                            last_text_disabled = '<button class="linkbutton" type="button" disabled="disabled">' + last_text + '</button>';
                            previous_text = '<button class="linkbutton" type="button">' + previous_text + '</button>';
                            first_text = '<button class="linkbutton" type="button">' + first_text + '</button>';
                            next_text = '<button class="linkbutton" type="button">' + next_text + '</button>';
                            last_text = '<button class="linkbutton" type="button">' + last_text + '</button>';
                            buttons = true;
                        }
                    }
                    if (page_number === undefined){
                        page_number = 1;
                    } else {
                        page_number = parseInt(page_number);
                    }
                    total_pages = Math.ceil(total_records / page_size);
                    if (page_number > 1){
                        first_page = '<a href="?' + MAG.DISPLAY.create_new_query({'page': 1}) + '">' + first_text + '</a>';
                        previous_string = '<a href="?' + MAG.DISPLAY.create_new_query({'page': (page_number-1)}) + '">' + previous_text + '</a>';
                    } else {
                        if (buttons == true) {
                            first_page = first_text_disabled;
                            previous_string = previous_text_disabled;
                        } else {
                            first_page = first_text;
                            previous_string = previous_text;
                        }
                    }
                    if (page_number < total_pages){
                        last_page = '<a href="?' + MAG.DISPLAY.create_new_query({'page': total_pages}) + '">' + last_text + '</a>';
                        next_string = '<a href="?' + MAG.DISPLAY.create_new_query({'page': (page_number+1)})+ '">' + next_text + '</a>';
                    } else {
                        if (buttons == true) {
                            last_page = last_text_disabled;
                            next_string = next_text_disabled;
                        } else {
                            last_page = last_text;
                            next_string = next_text;
                        }
                    }
                    option_string = '';
                    for (i=1; i<=total_pages; i+=1){
                        if (i === page_number){
                            option_string += '<option value="' + i + '" selected="selected">' + i + '</option>';
                        } else {
                            option_string += '<option value="' + i + '">' + i + '</option>';
                        }
                    }
                    select_string = '<select id="page_select">' + option_string + '</select>';
                    if (buttons){
                        container.innerHTML =  first_page + previous_string + ' page ' + select_string + ' of ' + total_pages + ' ' + next_string + last_page;
                    } else {
                        container.innerHTML =  first_page + ' | ' +  previous_string + ' | page ' + select_string + ' of ' + total_pages + ' | ' + next_string  + ' | ' +   last_page;
                    }
                    MAG.EVENT.addEventListener(document.getElementById('page_select'), 'change', function(event) {
                        window.location = '?' + MAG.DISPLAY.create_new_query({'page': (parseInt(event.target.value))});
                    });
                }
                // End of submodule DISPLAY
            };
        }()) // No trailing comma for last submodule

        // End of module MAG
    };
}());

// Compatibility for old scripts.
var RAVEN = MAG;
