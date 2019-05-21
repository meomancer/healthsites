__author__ = 'Irwan Fathurrahman <irwan@kartoza.com>'
__date__ = '29/11/18'

from django.db.models import Count
from django.http.response import HttpResponseBadRequest
from rest_framework.response import Response
from rest_framework.views import APIView
from api.api_views.v2.schema import (
    ApiSchemaBase,
    ApiSchemaBaseWithoutApiKey,
    Parameters
)
from api.api_views.v2.utilities import BadRequestError
from api.api_views.v2.pagination import (
    PaginationAPI, LessThanOneException, NotANumberException
)
from api.api_views.v2.facilities.base_api import FacilitiesBaseAPIWithAuth
from api.utils import validate_osm_data, convert_to_osm_tag, create_osm_node
from core.settings.utils import ABS_PATH
from localities.models import Country
from localities.utils import parse_bbox
from localities_osm.models.locality import LocalityOSM
from localities_osm.serializer.locality_osm import LocalityOSMBasicSerializer
from localities_osm.utilities import get_all_osm_query


class FilterFacilitiesScheme(ApiSchemaBaseWithoutApiKey):
    schemas = [
        Parameters.country, Parameters.extent, Parameters.output
    ]


class ApiSchema(ApiSchemaBase):
    schemas = [Parameters.page] + FilterFacilitiesScheme.schemas


class GetFacilitiesBaseAPI(object):
    """
    Parent class that hold filtering method of healthsites
    """

    def get_country(self, country):
        """ This function is for get country object from request
        """
        # check by country
        if country == 'World':
            country = None
        if country:
            # getting country's polygon
            country = Country.objects.get(
                name__iexact=country)
        return country

    def get_healthsites(self, request):

        # check extent data
        extent = request.GET.get('extent', None)
        queryset = get_all_osm_query()
        if extent:
            try:
                polygon = parse_bbox(request.GET.get('extent'))
            except (ValueError, IndexError):
                raise BadRequestError('extent is incorrect format')
            queryset = queryset.in_polygon(polygon)

        # check by country
        country = request.GET.get('country', None)
        try:
            country = self.get_country(country)
            if country:
                polygons = country.polygon_geometry
                queryset = queryset.in_polygon(polygons)
        except Country.DoesNotExist:
            raise BadRequestError('%s is not found or not a country.' % country)
        return queryset


class GetFacilities(PaginationAPI, FacilitiesBaseAPIWithAuth, GetFacilitiesBaseAPI):
    """
    get:
    Returns a list of facilities with some filtering parameters.

    post:
    Create new facility.
    """
    filter_backends = (ApiSchema,)

    def get(self, request):
        validation = self.validation()
        if validation:
            return HttpResponseBadRequest(validation)

        try:
            queryset = self.get_query_by_page(self.get_healthsites(request))
        except (LessThanOneException, NotANumberException) as e:
            return HttpResponseBadRequest('%s' % e)

        return Response(self.serialize(queryset, many=True))

    def post(self, request):
        data = request.data
        # Now, we post the data directly to OSM.
        try:
            # Validate data
            is_valid, message = validate_osm_data(data)
            if not is_valid:
                return HttpResponseBadRequest(message)

            # Map Healthsites tags to OSM tags
            mapping_file_path = ABS_PATH('api', 'fixtures', 'mapping.yml')
            data['tag'] = convert_to_osm_tag(
                mapping_file_path, data['tag'], 'node')

            # Push data to OSM
            user = request.user
            response = create_osm_node(user, data)

            return Response(response)

        except Exception as e:
            return HttpResponseBadRequest('%s' % e)


class GetFacilitiesCount(APIView, GetFacilitiesBaseAPI):
    """
    get:
    Returns count of facilities with some filtering parameters.
    """
    filter_backends = (FilterFacilitiesScheme,)

    def get(self, request):
        try:
            return Response(self.get_healthsites(request).count())
        except BadRequestError as e:
            return HttpResponseBadRequest('%s' % e)


class GetFacilitiesStatistic(APIView, GetFacilitiesBaseAPI):
    """
    get:
    Returns statistic of facilities with some filtering parameters.
    """
    filter_backends = (FilterFacilitiesScheme,)

    def get(self, request):
        try:
            healthsites = self.get_healthsites(request)
            output = {
                'localities': healthsites.count(),
                'numbers': {},
                'last_update': []
            }
            numbers = healthsites.values(
                'amenity').annotate(total=Count('amenity')).order_by('-total')
            for number in numbers[:5]:
                type = number['amenity']
                if type:
                    output['numbers'][type] = number['total']

            # get completeness
            basic = LocalityOSM.get_count_of_basic(healthsites)
            complete = LocalityOSM.get_count_of_complete(healthsites)
            output['completeness'] = {
                'basic': basic,
                'complete': complete
            }

            # last update
            healthsites = healthsites.exclude(
                changeset_timestamp__isnull=True).order_by(
                '-changeset_timestamp')[:10]
            output['last_update'] = LocalityOSMBasicSerializer(healthsites, many=True).data

            country = request.GET.get('country', None)
            country = self.get_country(country)
            if country:
                output['geometry'] = country.polygon_geometry.geojson
            return Response(output)
        except BadRequestError as e:
            return HttpResponseBadRequest('%s' % e)
