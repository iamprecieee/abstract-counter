from rest_framework.views import APIView
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from .services import CounterDeploymentService
from asgiref.sync import async_to_sync
from rest_framework.throttling import AnonRateThrottle
from rest_framework.exceptions import Throttled


class HomeView(APIView):
    """Main Page View"""
    
    def get(self, request):
        return render(request, 'deployer/index.html')
    
    
class PrepareDeploymentView(APIView):
    throttle_classes = [AnonRateThrottle]
    
    """API endpoint to prepare contract deployment"""
    
    @staticmethod
    async def get_deployment_result(service):
        return await service.prepare_deployment()
    
    def post(self, request):
        try:
            service = CounterDeploymentService()
            result = async_to_sync(self.get_deployment_result)(service)
            return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
          
            
class VerifyContractView(APIView):
    throttle_classes = [AnonRateThrottle]
    
    """API endpoint to verify deployed contract"""
    
    @staticmethod
    async def get_verification_result(service, contract_address):
        return await service.verify_contract(contract_address)
    
    def post(self, request):
        try: 
            contract_address = request.data.get('contract_address')
            service = CounterDeploymentService()
            result = async_to_sync(self.get_verification_result)(service, contract_address)
            return Response({
                'success': result['success']},
                status=status.HTTP_200_OK if result['success'] else status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
class HealthCheckView(APIView):
    def get(self, request):
        return Response({'status':'OK'}, status=status.HTTP_200_OK)