/*global window, document, localStorage, XMLHttpRequest, Element,
  ActiveXObject, SITE_DOMAIN, APP_NAME, MAG */
/*jslint nomen: true*/

var db;

var EXAMPLE_STATE = {
    author: "51a40ce2c6ec494fcbf56e46",
    citationwork: "50ffee9249d52407f946d879",
    comcitation: "50bcb46a49d524226a4ee08e",
    edition: "505863bf49d52476bfdd3c52",
    onlinecorpus: "5029636149d52414fc0000d4",
    series: "502962b349d52414fc0000d1",
}

/**

- Get local state
0. Get state from server if possible, if not stop sync
1. Check for object stores
2. Create object stores
3. Fill object stores

*/

var SYNC = (function () {
    "use strict";
    return {
        // body of module here


        init: function() {
            SYNC.check_for_meta_store()
        },

        /** 1. We need a meta store. */
        check_for_meta_store: function() {
            var request = indexedDB.open(LOCAL_DB_NAME);
            request.onerror = function(event) {
                alert("Why didn't you allow my web app to use IndexedDB?!");
            };
            request.onsuccess = function(event) {
                var db, transaction;
                db = request.result;
                if (db.objectStoreNames.contains('_meta')) {
                    SYNC.check_local_state();
                } else {
                    SYNC.create_meta_store(db.version);
                }
            };
        },

        /** 1a. Make the meta store. */
        create_meta_store: function(version) {
            var new_version, open_request;
            new_version = version + 1;
            open_request = indexedDB.open(LOCAL_DB_NAME, new_version);
            open_request.onupgradeneeded = function(event) { 
                var db = event.target.result;
                var object_store = db.createObjectStore("_meta", { keyPath: "_id" });
            };
            open_request.onsuccess = function(event) {
                SYNC.check_local_state();
            };
        },
        
        /** 2. We need a local state object. */
        check_local_state: function() {
            var request = indexedDB.open(LOCAL_DB_NAME);
            request.onsuccess = function(event) {
                var db = event.target.result;
                db.transaction("_meta").objectStore("_meta").get("state").onsuccess = function(event) {
                    var status = event.target.result;
                    if (typeof status == "undefined") {
                        SYNC.create_local_state()
                    } else {
                        // Do something, go to the next step
                        SYNC.get_remote_state(status)
                    }
                };
            };
        },
 
        /** 2a. Make the local state object. */
        create_local_state: function() {
            var request = indexedDB.open(LOCAL_DB_NAME);
            request.onsuccess = function(event) {
                var db = event.target.result;
                var transaction = db.transaction(["_meta"], "readwrite");
                var object_store = transaction.objectStore("_meta");
                var blank_state = {'_id': 'state'};
                var add_request = object_store.add(blank_state);
                add_request.onsuccess = function(event) {
                    // Go to the next step
                    SYNC.get_remote_state(blank_state);
                };
            };   
        },

        /** 3. Try to get the remote state object,
               if we fail then sync has failed
               since we are offline */
        get_remote_state: function (local_state) {
            var url, options;
            url = 'http://' + SITE_DOMAIN + '/api/_sync/state/' + APP_NAME + '/';
            if (typeof options === "undefined") {
                options = {
                    success: function (remote) {
                        var info = {local_state: local_state,
                                    remote_state: remote.state}
                        SYNC.check_for_relevant_object_stores(info);
                    }
                };
            }
            MAG._REQUEST.request(url, options);
        },

        /** 4. Check for object stores */
        check_for_relevant_object_stores: function(info) {
            var open_request;
            open_request = indexedDB.open(LOCAL_DB_NAME);
            open_request.onsuccess = function(event) {
                var db, resource_type;
                db = event.target.result;
                info.version = db.version;
                info.present = []
                info.missing = []

                // Check for resources
                for (resource_type in info.remote_state) {
                    if (info.remote_state.hasOwnProperty(resource_type)) {
                        if (db.objectStoreNames.contains(resource_type)) {
                            info.present[info.present.length] = resource_type;
                        } else {
                            info.missing[info.missing.length] = resource_type;
                        }
                    }
                }
                if (info.missing.length > 0) {
                    SYNC.create_missing_object_stores(info);
                } else {
                    // skip to the next step.
                }
            };
        },

        /** 5. Create missing stores **/
        create_missing_object_stores: function(info) {
            var new_version, open_request, resource_type;
            info.version += 1;
            open_request = indexedDB.open(LOCAL_DB_NAME, info.version);
            open_request.onupgradeneeded = function(event) {
                var db, object_store, resource_type, i, length;
                db = event.target.result;
                
                // Create resource stores
                length = info.missing.length;
                for (i = 0; i < length; i += 1) {
                    resource_type = info.missing[i];
                    console.log('Missing object store: ' + resource_type);
                    object_store = db.createObjectStore(
                        resource_type, { keyPath: "_id" });
                    console.log('Created object store for: ' + resource_type);
                }
            };

            open_request.onsuccess = function() {
                console.log('We have the stores');
                SYNC.populate_empty_stores(info);
                SYNC.update_existing_object_stores(info);
            };
        },

        /** 6. Populate empty stores. */
        populate_empty_stores: function(info) {
            var length, i;
            length = info.missing.length;
            for (i = 0; i < length; i += 1) {
                SYNC.get_all_instances(info.missing[i], info);
            }
        },

        /** 6a. Get all the instances from remote server. */
        get_all_instances: function (resource, info) {
            var base_url, url, options, success;
            success = function(results) {
                SYNC.populate_instances(results.results, resource, info);
            }
            options = {success:success};
            base_url = MAG._STORAGE.get_data_from_storage_or_function(
                "MAG._REST.get_api_url"
            );
            url = base_url + resource + '/';
            MAG._REQUEST.request(url, options);
        },        

        /** 6b. Populate the empty stores with the remote instances. */
        populate_instances: function (instances, resource, info) {
            var open_request;
            open_request = indexedDB.open(LOCAL_DB_NAME);
            open_request.onsuccess = function(e) {
                var length, i, transaction, object_store, add_request;
                console.log('Populating: ' + resource);
                db = e.target.result;
                var transaction = db.transaction([resource], "readwrite");

                transaction.oncomplete = function(event) {
                    SYNC.update_local_state(
                        resource,
                        info.remote_state[resource]);
                };
 
                transaction.onerror = function(event) {
                    // Don't forget to handle errors!
                    console.log("Error!");
                };
 
                object_store = transaction.objectStore(resource);

                length = instances.length;
                for (i = 0; i < length; i += 1) {
                    add_request = object_store.add(instances[i]);
                    add_request.onsuccess = function(event) {};
                }
            };
            open_request.onerror = function(event) {
                alert("Database error: " + event.target.errorCode);
                console.log("Database error: " + event.target.errorCode);
            };
        },

        /** 7. Update existing stores. */
        update_existing_object_stores: function(info) {
            var length, i, resource_type, old_state, new_state;
            length = info.present.length;
            for (i = 0; i < length; i += 1) {
                resource_type = info.present[i];
                old_state = info.local_state[resource_type]
                new_state = info.remote_state[resource_type]
                if (old_state == new_state) {
                    console.log(resource_type + " is up to date.");
                } else {
                    console.log(resource_type + " needs to be updated.");
                    SYNC.get_update(resource, old_state, new_state);
                }
            }
        },

        /** 7a. get the updated instances. */
        get_update: function (resource, objectid, new_state) {
            var base_url, url;
            base_url = MAG._STORAGE.get_data_from_storage_or_function(
                "MAG._REST.get_api_url"
            );
            url = base_url + '_sync/update/' + resource + '/' + objectid + '/';
            MAG._REQUEST.request(url, {
                success: function (items) {
                    SYNC.do_update_store(items, resource, new_state);
                }
            });
        },

        /** 7b. store the updated instances */
        do_update_store: function(items, resource, new_state) {
            var open_db_request, object_store, up_transaction, item;
            open_db_request = indexedDB.open(LOCAL_DB_NAME);
            open_db_request.onsuccess = function(event) {
                var db, i, length, up_transaction;
                db = event.target.result;
                up_transaction = db.transaction([resource], "readwrite");
                up_transaction.oncomplete = function(event) {
                    SYNC.update_local_state(
                        resource,
                        new_state);
                };
                up_transaction.onerror = function(event) {
                    // Don't forget to handle errors!
                    console.log("Up transaction error!");
                };
                object_store = up_transaction.objectStore(resource);
                // Main loop!
                length = items.length;
                for (i = 0; i < length; i += 1) {
                    item = items[i];
                    console.log('Made it here!');
                    switch (item.operation) {
                        case "create":
                            SYNC.add_instance(object_store, item)
                            break;
                        case "delete":
                            SYNC.delete_instance(object_store, item)
                            break;
                        case "update":
                            SYNC.update_instance(object_store, item)
                            break;
                    };
                }
            };
        },

        add_instance: function(object_store, item) {
            object_store.add(item.document);
        },

        delete_instance: function(object_store, item) {
            object_store.delete(item.document);
        },

        update_instance: function(object_store, item) {
            object_store.put(item.document);
        },

        /** 8. Update local meta state */
        update_local_state: function(resource, objectid) {
            var request = indexedDB.open(LOCAL_DB_NAME);
            request.onsuccess = function(event) {
                var db = event.target.result;
                db.transaction("_meta").objectStore("_meta").get("state").onsuccess = function(event) {
                    var state = event.target.result;
                    var put_request = indexedDB.open(LOCAL_DB_NAME);
                    put_request.onsuccess = function(event) {
                        state[resource] = objectid;
                        console.log('state is...');
                        console.log(state);
                        db = request.result;
                        var transaction = db.transaction(["_meta"], "readwrite");
                        transaction.oncomplete = function(event) {
                            console.log("Meta updated for " + resource);
                        };
                        var object_store = transaction.objectStore("_meta");
                        object_store.put(state);
                    };

                };
            };
        },


        // End of module SYNC
    };
}());

