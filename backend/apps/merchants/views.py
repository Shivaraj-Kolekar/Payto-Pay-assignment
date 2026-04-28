from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.merchants.serializers import MerchantDashboardSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return current merchant's dashboard data with balance info."""
    serializer = MerchantDashboardSerializer(request.user)
    return Response(serializer.data)
