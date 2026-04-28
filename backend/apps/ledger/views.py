from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ledger.models import LedgerEntry
from apps.ledger.serializers import LedgerEntrySerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ledger_list(request):
    """List all ledger entries for the authenticated merchant."""
    entries = LedgerEntry.objects.filter(merchant=request.user).order_by('-created_at')
    serializer = LedgerEntrySerializer(entries, many=True)
    return Response(serializer.data)
