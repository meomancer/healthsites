__author__ = 'Irwan Fathurrahman <irwan@kartoza.com>'
__date__ = '29/11/18'

from django.http.response import Http404, HttpResponseBadRequest
from rest_framework.response import Response
from api.api_views.v2.facilities.base_api import (
    BaseAPI
)
from localities.models import Locality


class GetDetailFacility(BaseAPI):
    """
    get:
    Returns a facility detail.

    put:
    Update a facility.
    There are mandatory field for this:
    1. uuid : this is path parameters
    2. name
    3. lng & lat
    4. and some of required specification that will be show the error
    on the result (this specification is defined at admin site)

    5. Some attributes that has options. Can put other, but it will not be show
    on the healthsites map. This attributes should be array and can be more than one
    "activities": [
            "medicine and medical specialties",
            "surgery and surgical specialties",
            "Maternal and women health",
            "pediatric care"
        ],
    "ancillary_services": [
        "Operating theater",
        "laboratory",
        "imaging equipment",
        "intensive care unit"
    ],
    "scope_of_service": [
        "specialized care",
        "general acute care",
        "rehabilitation care",
        "old age/hospice care"
    ],

    6. Some attributes has it's own format
    "inpatient_service": {
        "full_time_beds": "3",
        "part_time_beds": "2"
    },
    "defining_hours": {
        "wed": [
            "09:00-17:00",
            "20:00-23:00",
        ],
        "sun": [],
        "fri": [],
        "tue": [],
        "mon": [],
        "thu": [],
        "sat": []
    },
    "staff": {
        "nurses": "1",
        "doctors": "3"
    }

    7. Some attributes is just 1 value but has options,
    will be error if not in these options.

    nature_of_facility : [
        public,
        private not for profit,
        private commercial]
    ownership : [
        clinic without beds,
        clinic with beds,
        first referral hospital,
        second referral hospital or General hospital,
        tertiary level including University hospital]
    """

    def get(self, request, uuid):
        try:
            facility = Locality.objects.get(uuid=uuid)
            return Response(self.serialize(facility))
        except Locality.DoesNotExist:
            raise Http404()

    def put(self, request, uuid):
        try:
            data = request.data
            facility = Locality.objects.get(uuid=uuid)
            try:
                facility.update_data(data, request.user)
                return Response('OK')
            except KeyError as e:
                return HttpResponseBadRequest('%s is required' % e)
            except ValueError as e:
                return HttpResponseBadRequest('%s' % e)
            except TypeError as e:
                return HttpResponseBadRequest('%s' % e)
        except Locality.DoesNotExist:
            raise Http404()

    def delete(self, request, uuid):
        try:
            facility = Locality.objects.get(uuid=uuid)
            facility.delete()
            return Response('OK')
        except Locality.DoesNotExist:
            raise Http404()