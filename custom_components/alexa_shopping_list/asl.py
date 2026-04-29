#!/usr/bin/env python3

import websockets
import json
import datetime
import os
import asyncio
import hashlib

# ============================================================


class AlexaShoppingListSync:

    def __init__(self, ip="localhost", port=4000, sync_mins=60, hasl_path=None, hasl_refresh=None):
        self.uri = "ws://"+ip+":"+str(port)
        self._hasl_path = hasl_path
        self._hasl_refresh = hasl_refresh
        self._setup_cached_list(sync_mins * 60)
        self._sync_lock = asyncio.Lock()
        self.is_authenticated = True

    # ============================================================
    # Helpers


    async def _send_command(self, command, **kwargs):
        async with websockets.connect(self.uri) as websocket:
            request = {
                'command': command,
                'args': {
                    **kwargs
                }
            }
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            return json.loads(response)
    

    def _command_successful(self, response):
        if "error" in response and response['error'] != None:
            if response['error'] == "Not authenticated":
                self.is_authenticated = False
            return False
        self.is_authenticated = True
        return True
    

    def _command_result(self, response):
        if "result" in response:
            return response['result']
        return None
    

    def _command_error(self, response):
        if "error" in response:
            return response['error']
        return None
        

    # ============================================================
    # Server


    async def can_ping_server(self):
        response = await self._send_command("ping")
        if self._command_successful(response):
            if self._command_result(response) == "pong":
                return True
        return False
    

    async def server_config_is_valid(self):
        response = await self._send_command("config_valid")
        if self._command_successful(response):
            return self._command_result(response)
        return False
    

    async def server_is_authenticated(self):
        response = await self._send_command("authenticated")
        if self._command_successful(response):
            result = self._command_result(response)
            self.is_authenticated = bool(result)
            return self.is_authenticated
        return False
    
    async def get_server_auth_cached_state(self):
        try:
            response = await self._send_command("config_get", key="auth_checked_time")
            if self._command_successful(response):
                result = self._command_result(response)
                self.is_authenticated = bool(result and int(result) > 0)
                return self.is_authenticated
            return False
        except Exception:
            return self.is_authenticated

    # ============================================================
    # Cache


    def _setup_cached_list(self, sync_seconds):
        self._sync_seconds = sync_seconds
        self.last_updated = None
        self._cached_list = []
    

    def _update_cached_list(self, new_list):
        if new_list is None:
            return
        self._cached_list = new_list
        self.last_updated = datetime.datetime.now().astimezone()
    

    def _cached_list_needs_updating(self):
        if self.last_updated == None:
            return True

        now = datetime.datetime.now().astimezone()
        diff = now - self.last_updated

        if diff.total_seconds() >= self._sync_seconds:
            return True
        return False


    # ============================================================
    # Commands


    async def _get_list(self, force = False):
        if self._cached_list_needs_updating() or force:
            response = await self._send_command("get_list")
            if self._command_successful(response):
                self._update_cached_list(self._command_result(response))
            else:
                raise Exception(self._command_error(response))
        return self._cached_list
    

    async def _add_item(self, item):
        response = await self._send_command("add_item", item=item)
        if self._command_successful(response):
            self.last_updated = None
        else:
            raise Exception(self._command_error(response))
        return self._cached_list
    

    async def _update_item(self, old, new):
        response = await self._send_command("update_item", old=old, new=new)
        if self._command_successful(response):
            self.last_updated = None
        else:
            raise Exception(self._command_error(response))
        return self._cached_list
    

    async def _remove_item(self, item):
        response = await self._send_command("remove_item", item=item)
        if self._command_successful(response):
            self.last_updated = None
        else:
            raise Exception(self._command_error(response))
        return self._cached_list


    async def _bulk_apply_changes(self, add_items=None, remove_items=None, update_items=None):
        response = await self._send_command(
            "bulk_apply_changes",
            add_items=add_items or [],
            remove_items=remove_items or [],
            update_items=update_items or []
        )
        if self._command_successful(response):
            self.last_updated = None
        else:
            raise Exception(self._command_error(response))
        return self._cached_list

    # ============================================================
    # Sync


    async def homeassistant_shopping_list_updated(self, event):
        await self.sync(None, True)
    

    def _export_ha_shopping_list(self, items):
        export = []
        for item in items:
            export.append({
                "id": hashlib.md5(item.encode('utf-8')).hexdigest()[:12],
                "name": item,
                "complete": False
            })
        
        with open(self._hasl_path, "w") as outfile:
            outfile.write(json.dumps(export, indent=4))
    

    def _read_ha_shopping_list(self):
        if os.path.exists(self._hasl_path):
            with open(self._hasl_path, 'r') as file:
                return json.load(file)
        return []
    

    def _ha_shopping_list_hash(self):
        serialized = json.dumps(self._read_ha_shopping_list(), sort_keys=True)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()
    

    def _sync_state_path(self):
        return os.path.join(
            os.path.dirname(self._hasl_path),
            ".alexa_shopping_list_sync_state.json"
        )


    def _read_last_synced_active_items(self):
        path = self._sync_state_path()
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            items = data.get("last_synced_active_items")
            if isinstance(items, list):
                return items
        except Exception:
            pass

        return None


    def _write_last_synced_active_items(self, items):
        path = self._sync_state_path()
        tmp_path = path + ".tmp"
        data = {
            "last_synced_active_items": sorted(set(items), key=str.casefold),
            "updated_at": datetime.datetime.now().astimezone().isoformat(),
        }

        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        os.replace(tmp_path, path)
    

    def _find_ha_list_item(self, find, ha_list):
        for item in ha_list:
            if item['name'] == find:
                return item
        return None
    

    async def _debug_log_entry(self, logger=None, entry=""):
        if logger == None:
            return
        logger.debug(entry)


    async def _do_sync(self, loop, logger=None, force=False):

        ha_list = await loop.run_in_executor(None, self._read_ha_shopping_list)
        original_ha_list_hash = await loop.run_in_executor(None, self._ha_shopping_list_hash)
        
        await self._debug_log_entry(logger, "Loading Alexa shopping list")
        alexa_list = await self._get_list(force)
        await self._debug_log_entry(logger, "Alexa list: "+json.dumps(alexa_list))

        last_synced_active_items = await loop.run_in_executor(
            None,
            self._read_last_synced_active_items
        )

        ha_active_names = []
        ha_completed_names = []
        for item in ha_list:
            name = item['name']
            if item.get('complete') == True:
                ha_completed_names.append(name)
            else:
                ha_active_names.append(name)

        to_add = []
        to_remove = []

        for name in ha_completed_names:
            if name in alexa_list:
                to_remove.append(name)

        for name in ha_active_names:
            if name not in alexa_list:
                to_add.append(name)

        if last_synced_active_items is not None:
            for name in last_synced_active_items:
                if (
                    name in alexa_list
                    and name not in ha_active_names
                    and name not in ha_completed_names
                ):
                    to_remove.append(name)
        else:
            await self._debug_log_entry(
                logger,
                "No previous sync snapshot found; not inferring HA deletes on this run"
            )

        to_add = sorted(set(to_add), key=str.casefold)
        to_remove = sorted(set(to_remove), key=str.casefold)

        await self._debug_log_entry(logger, "To add to alexa: "+json.dumps(to_add))
        await self._debug_log_entry(logger, "To remove from alexa: "+json.dumps(to_remove))
        if len(to_add) + len(to_remove) > 1:
            await self._debug_log_entry(logger, "Applying Alexa changes in bulk")
            await self._bulk_apply_changes(add_items=to_add, remove_items=to_remove)
        else:
            for item in to_add:
                await self._add_item(item)
            for item in to_remove:
                await self._remove_item(item)
        
        # Force a fresh scrape after add/remove operations. A mutation response or
        # cached list can be stale/partial if Amazon's virtualized list is scrolled.
        refreshed_items = await self._get_list(force=bool(to_add or to_remove))
        await self._debug_log_entry(logger, "Refreshed Alexa list: "+json.dumps(refreshed_items))

        # Defensive guard: after adding/removing items, do not allow an obviously
        # truncated post-mutation scrape to overwrite Home Assistant's local list.
        if (to_add or to_remove) and len(refreshed_items) < len(alexa_list) - len(to_remove):
            await self._debug_log_entry(
                logger,
                "Refreshed Alexa list looks truncated; refusing to export to HA. "
                f"before={len(alexa_list)} "
                f"refreshed={len(refreshed_items)} "
                f"to_add={json.dumps(to_add)} "
                f"to_remove={json.dumps(to_remove)}"
            )
            return False

        await self._debug_log_entry(logger, "Exporting new HA shopping list")
        await loop.run_in_executor(None, self._export_ha_shopping_list, refreshed_items)
        await loop.run_in_executor(None, self._write_last_synced_active_items, refreshed_items)
        await self._hasl_refresh()


        await self._debug_log_entry(logger, "Original list hash: "+original_ha_list_hash)
        new_ha_list_hash = await loop.run_in_executor(None, self._ha_shopping_list_hash)
        await self._debug_log_entry(logger, "New list hash: "+new_ha_list_hash)
        if original_ha_list_hash != new_ha_list_hash:
            await self._debug_log_entry(logger, "List changed")
            return True
        else:
            await self._debug_log_entry(logger, "List did not change")
            return False

    
    async def sync(self, logger=None, force=False):
        loop = asyncio.get_running_loop()

        if os.path.exists(self._hasl_path) == False:
            await self._debug_log_entry(logger, "HA shopping list file not found - creating empty list")
            await loop.run_in_executor(None, self._export_ha_shopping_list, [])

        if self._cached_list_needs_updating() == False and force == False:
            return False
        
        if self._sync_lock.locked():
            await self._debug_log_entry(logger, "Sync already in progress, skipping")
            return False

        result = False
        async with self._sync_lock:
            try:
                result = await self._do_sync(loop, logger, force)
            except Exception as e:
                await self._debug_log_entry(logger, f"Sync error: {type(e).__name__}: {e}")

        return result
    # ============================================================

