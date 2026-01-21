from django.http import JsonResponse, response
from django.http.request import HttpRequest
from time import time


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


def get_next_bet_sync_time(_: HttpRequest) -> JsonResponse:
    with open("./next_block_sync.txt", "r") as file:
        next_bet_sync = int(file.readline().strip())
    response = {
        "nextBetSync": next_bet_sync,
    }
    print(next_bet_sync)
    return JsonResponse(response)
