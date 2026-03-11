from django.http import JsonResponse, response
from django.http.request import HttpRequest
from time import time
import os


# NTP protocol implementation
# ct -> client time in unix milliseconds
def get_time(request: HttpRequest) -> JsonResponse:
    client_time = int(request.GET["ct"])
    server_timestamp = int(time() * 1000)
    diff = server_timestamp - client_time
    response = {
        "diff": diff,
        "serverTimestamp": server_timestamp,
    }
    return JsonResponse(response)


# 10 minutes, same as bet_manager BLOCK_REFRESH_PERIOD
DEFAULT_NEXT_BLOCK_OFFSET_MS = 10 * 60 * 1000


def get_next_bet_sync_time(_: HttpRequest) -> JsonResponse:
    # Try project root and webapp dir (Docker vs local run)
    for path in ("./next_block_sync.txt", "next_block_sync.txt", "webapp/next_block_sync.txt"):
        try:
            with open(path, "r") as file:
                next_bet_sync = int(file.readline().strip())
            break
        except (FileNotFoundError, ValueError):
            continue
    else:
        # File missing or invalid: use now + 10 min so timer shows ~10:00
        next_bet_sync = int(time() * 1000) + DEFAULT_NEXT_BLOCK_OFFSET_MS
    response = {
        "nextBetSync": next_bet_sync,
    }
    return JsonResponse(response)
