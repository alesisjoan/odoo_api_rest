# -*- coding: utf-8 -*-
import web
import xmlrpclib
import json
import base64


username = 'admin' #the user
pwd = 'YWRtaW4='      #YWRtaW4=
dbname = 'hcud_gh'    #the database
# https://www.freeformatter.com/url-encoder.html#ad-output
odoo_host = 'http://localhost:8069'

# uid = 1


urls = (
    '/partner(.*)', 'Partner',
    '/diagnostico(.*)', 'Diagnostico',
    '/receta_ambulatorio(.*)', 'RecetaAmbulatorio',
    '/receta_internados(.*)', 'RecetaInternados',
    '/producto(.*)', 'Producto',
    '/base64/(.*)', 'Base_64',
)
app = web.application(urls)
models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(odoo_host))


class ErrorMessage(object):

    def __init__(self, error_code, message):
        self.message = message
        self.type_error = error_code


class OdooGateway(object):

    result = {}

    common = False

    def login(self, dbname, username, pwd, web):
        if not dbname:
            result = ErrorMessage('HEM00', 'Debe seleccionar una base de datos.').__dict__
            return 0, result
        if not pwd:
            result = ErrorMessage('HEM00', 'Debe ingresar una contraseña.').__dict__
            return 0, result
        if not username:
            result = ErrorMessage('HEM00', 'Debe ingresar un usuario.').__dict__
            return 0, result
        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(host))
        uid = common.authenticate(dbname, username, pwd, {})
        if not uid:
            web.ctx.status = '401 Unauthorized'
            result = ErrorMessage('HEM01', 'Datos de login incorrectos.').__dict__
            return 0, result
        print "Login exitoso para %s en %s" % (h(username), h(dbname))
        return uid, ''

    def search(self, dbname, uid, pwd, model, criteria, offset=0, limit=1, fields=''): # TODO order
        if not criteria:
            criteria = [['id','>',0]]
        if limit > 1001:
            result = ErrorMessage('HEM01', 'Se permite un limite de hasta 1000 registros.').__dict__
            return result
        result = models.execute_kw(dbname, uid, pwd, model, 'search_read', [criteria], {'fields': fields, 'limit': limit})
        return result

    def create(self, dbname, uid, pwd, model, vals, fields='', limit=1):
        id = models.execute_kw(dbname, uid, pwd, model, 'create', [vals])
        result = self.search(dbname, uid, pwd, model, [['id','=',id]], 0, 1, fields)
        return result

    def write(self, dbname, uid, pwd, model, id, vals, fields):
        models.execute_kw(dbname, uid, pwd, model, 'write', [[id], vals])
        result = self.search(dbname, uid, pwd, model, [['id','=',id]], 0, 1, fields)
        return result

    def delete(self, dbname, uid, pwd, model, id):
        result = self.search(dbname, uid, pwd, model, [['id', '=', id]], 0, 1, {})
        if not result:
            return 'No se encuentra el objeto solicitado con id %s' % str(id)
        models.execute_kw(dbname, uid, pwd, model, 'unlink', [[id]])
        # check if the deleted record is still in the database
        result = self.search(dbname, uid, pwd, model, [['id', '=', id]], 0, 1, {})
        if not result:
            result = 'OK'
        return result

odoo = OdooGateway()


class WebInit(object):

    def _web_init(self, web):
        web.header('Content-Type', 'text/plain;charset=UTF-8')
        data = web.input()
        passwd = base64.b64decode(data.password)
        return data, passwd

    def GET(self, url):
        data, passwd = self._web_init(web)
        criteria = eval(data.criteria) if data.criteria else ''
        offset = int(data.offset)
        limit = int(data.limit)
        uid, message = odoo.login(data.dbname, data.user, passwd, web)
        result = message if not uid else odoo.search(data.dbname, uid, passwd, self._model_name(), criteria, offset, limit, self._default_fields())
        return to_json(result)

    def POST(self, url):
        data, passwd = self._web_init(web)
        vals = eval(data.vals) if data.vals else ''
        uid, message = odoo.login(data.dbname, data.user, passwd, web)
        result = message if not uid else odoo.create(data.dbname, uid, passwd, self._model_name(), vals, self._default_fields())
        return to_json(result)

    def PUT(self, url):
        data, passwd = self._web_init(web)
        vals = eval(data.vals) if data.vals else ''
        id = int(data.id)
        uid, message = odoo.login(data.dbname, data.user, passwd, web)
        result = message if not uid else odoo.write(data.dbname, uid, passwd, self._model_name(), id, vals, self._default_fields())
        return to_json(result)

    def DELETE(self, url):
        data, passwd = self._web_init(web)
        id = int(data.id)
        uid, message = odoo.login(data.dbname, data.user, passwd, web)
        result = message if not uid else odoo.delete(data.dbname, uid, passwd, self._model_name(), id)
        return to_json(result)


class Partner(WebInit):

    def _default_fields(self):
        return ['name', 'documento', 'sexo', 'email', 'fecha_nacimiento', 'zip', 'street', 'city', 'phone', 'mobile',
                'paciente', 'medico', 'afiliacion_id']

    def _model_name(self):
        return 'res.partner'


class Diagnostico(WebInit):

    def _default_fields(self):
        return ['id', 'name', 'descripcion']

    def _model_name(self):
        return 'gestion_hospitalaria.diagnostico'


class RecetaAmbulatorio(WebInit):

    def _default_fields(self):
        return ['id', 'paciente_id', 'paciente_dni', 'fecha_vencimiento', 'medico_id', ]

    def _model_name(self):
        return 'gestion_hospitalaria.receta_ambulatorio'


class RecetaInternados(WebInit):

    def _default_fields(self):
        return ['id', 'paciente_id', 'paciente_dni', 'fecha_vencimiento', 'medico_id', ]

    def _model_name(self):
        return 'gestion_hospitalaria.receta_internados'


class Producto(WebInit):

    def _default_fields(self):
        return ['id', 'gtin', 'acciofar_id', 'tamanio', 'potencia', 'tipounid_id', 'active', 'name', 'forma_id',
                'troquel','upotenci_id', 'monodro_id', 'trazable']

    def _model_name(self):
        return 'product.template'


class Base_64:

    def GET(self, passwd):
        web.header('Content-Type', 'text/plain;charset=UTF-8')
        return base64.b64encode(passwd)


def to_json(result):
    json_object = json.dumps(result, indent=1, ensure_ascii=False, sort_keys=True)
    print json_object
    return json_object

def h(string):
    return colors.fg.green+string+colors.reset

class colors:
    '''Colors class:
    reset all colors with colors.reset
    two subclasses fg for foreground and bg for background.
    use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.green
    also, the generic bold, disable, underline, reverse, strikethrough,
    and invisible work with the main class
    i.e. colors.bold
    '''
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    underline='\033[04m'
    reverse='\033[07m'
    strikethrough='\033[09m'
    invisible='\033[08m'
    class fg:
        black='\033[30m'
        red='\033[31m'
        green='\033[32m'
        orange='\033[33m'
        blue='\033[34m'
        purple='\033[35m'
        cyan='\033[36m'
        lightgrey='\033[37m'
        darkgrey='\033[90m'
        lightred='\033[91m'
        lightgreen='\033[92m'
        yellow='\033[93m'
        lightblue='\033[94m'
        pink='\033[95m'
        lightcyan='\033[96m'
    class bg:
        black='\033[40m'
        red='\033[41m'
        green='\033[42m'
        orange='\033[43m'
        blue='\033[44m'
        purple='\033[45m'
        cyan='\033[46m'
        lightgrey='\033[47m'


if __name__ == "__main__":
    app.run()