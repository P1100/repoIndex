from .__init__ import *
from .hostManager import *
from jsonschema import validate
from bson.json_util import dumps
import pymongo
import requests
import os
import paramiko
import bcrypt

genID_schema = {
    "type" : "object",
    "properties" : {
        "genID" : {"type" : "array"},
    },
    "required": ["genID"]
}

descr_schema = {
    "type" : "object",
    "properties" : {
        "description" : {"type" : "string"},
    },
    "required": ["description"]
}

@method_decorator([login_required], name='dispatch')
class LandAddExperiment(View):
    def get(self, request):
        return render(request, 'repoIndex/addExperiment.html')

@method_decorator([login_required], name='dispatch')
class LandQueryExperimentType(View):
    def get(self, request):
        exp_types=db.experiment_types.find({},{"_id":0}).sort("Name",pymongo.ASCENDING)
        print('exp_types is:',exp_types)
        return render(request, 'repoIndex/queryExperimentType.html',{'exp_types': exp_types})

@method_decorator([login_required], name='dispatch')
class LandQueryExperiment(View):
    def get(self, request):
        return render(request, 'repoIndex/queryExperiment.html')

@method_decorator([login_required], name='dispatch')
class LandValidateGenID(View):
    def get(self, request):
        return render(request, 'repoIndex/validateGenID.html')

def validateJSONschema(json_file,schema):
    try:
        data = json.loads(json_file)
        validate(instance=data, schema=schema)
        print("JSON valid")
        return (data)
    except Exception as e:
        err_msg = "Error in validating JSON schema: " + str(e)
        # print(err_msg)
        return (err_msg)

def wrapvalidateJSONschema(json_file,schema,request):
    try:
        schema_valid = validateJSONschema(json_file,schema)
        if schema_valid != "OK":
            print(schema_valid)
            return RedirectIfWrong(request,'repoIndex/errorUploading.html',{'error_string': str(schema_valid)})
        return "OK"
    except Exception as e:
        err_msg = "Error in JSON schema validation function"
        print(err_msg)
        return RedirectIfWrong(request,'repoIndex/errorUploading.html',{'error_string': str(err_msg)})

def validateGenID(genID_list):
    try:
        print("Entered GenID validation")
        # print("genid list is:", genID_list)
        genIDs = json.dumps(genID_list)
        # print(genIDs)
        req_list=[]
        params = {'parameters': '[{"values": '+genIDs+', "id": 0}]', 'template_id': 10}
        # print(params)
        r = requests.post('https://las.ircc.it/mdam/api/runtemplate/', data=params, verify=False)
        resp = json.loads(r.text)
        # {'body': [['CRC0262LMX0A02202TUMD28000', 'False', '2019-05-09', '0', 'None', 'DNA', '344209'], ['CRC0262LMX0A02203TUMLS0100', 'True', '2019-04-11', '0', '2019-04-11', 'LabeledSection', '341690']], 'header': ['Genealogy ID', 'Availability', 'Sampling date', 'Time used', 'Archive date', 'Aliquot type', 'ID']}

        for el in resp['body']:
            # print("genID:",el[0])
            req_list.append(el[0])
        # print("req_list is:", req_list)
        diff = set(genID_list).symmetric_difference(set(req_list))
        # diff = [x for x in set(genID_list) if x not in set(req_list)]
        print("diff is:", len(diff))
        if len(diff) == 0:
            return ("OK")
        else:
            return (diff)
    except Exception as e:
        print ('Error validateGenID', e)
        return ("X")

@method_decorator([login_required], name='dispatch')
class AddExperiment(View):
    def post(self, request):
        try:
            print("entered AddExperiment")
            # print("request is: ",request.POST)
            print("request genID file is: ",request.FILES['exp_genID-file'])
            print("request descr file is: ",request.FILES['exp_descr-file'])

            hostname = request.POST['hostname']
            exp_name = request.POST['exp_name']
            exp_type = request.POST['exp_type']
            pipeline = request.POST['pipeline']

            wb_genID = request.FILES['exp_genID-file'].read()
            # print(wb_genID)
            # data_genID = json.loads(wb_genID)
            # print(data_genID)
            data_genID = validateJSONschema(wb_genID,genID_schema)
            print("schema_valid of genID file = OK")
            if "Error" in data_genID:
                print(data_genID)
                return render(request,'repoIndex/errorUploading.html',{'error_string': data_genID})
            
            wb_descr = request.FILES['exp_descr-file'].read()
            # print(wb_descr)
            # data_descr = json.loads(wb_descr)
            # print(data_descr)
            data_descr = validateJSONschema(wb_descr,descr_schema)
            print("schema_valid of description file = OK")
            if "Error" in data_descr:
                print(data_descr)
                return render(request,'repoIndex/errorUploading.html',{'error_string': data_descr})

            valid = validateGenID(data_genID['genID'])
            print("valid is:", valid)

            if valid == "OK":
                new_exp = db.experiments.update_one(
                    { 'exp_name': exp_name },
                    {"$setOnInsert":{
                        'exp_name': exp_name,
                        'genID': data_genID['genID'],
                        'exp_type': exp_type,
                        'pipeline': pipeline,
                        'description': data_descr['description']
                        }
                    },
                    upsert = True
                    )
                print("new_exp is:", new_exp.upserted_id)

                # key = getattr(settings, "SECRET_KEY", None)
                # print("key is ", key)

                host_cursor = db.hosts.find({"hostname": hostname}).limit(1)
                # print("password is: ", dumps(password))
                # username = db.hosts.find({"hostname": hostname}, {"_id": 0, "host_username": 1}).limit(1)
                # print("username is: ", dumps(username))
                # path = db.hosts.find({"hostname": hostname}, {"_id": 0, "host_path": 1}).limit(1)
                # print("path is: ", dumps(path))

                for doc in host_cursor:
                    print("doc is: ",doc)
                    exp_objID = doc['_id']
                    username = doc['host_username']
                    password = doc['host_password']
                    path = doc['host_path']

                # TODO put Fernet encr and decr in separate fcts
                key = b'n_jrI9S9ivI9iYQDEfVPqfntsxFyfSBp8375JFvIsxM='
                print("K:",key)
                f = Fernet(key)
                print("F:",f)
                encrypted_pw = password
                decrypted_pw = f.decrypt(encrypted_pw)
                print("ENC",encrypted_pw)

                # print(username['host_username'])
                # print(password['host_password'])
                # print(path['host_path'])

                conn_test = testConnection(hostname,username,decrypted_pw,path)
                print("conn_test is: ", conn_test)
                if conn_test != "OK":
                    print(conn_test)
                    return render(request, 'repoIndex/errorUploading.html',{'error_string': conn_test})

                # TODO create file and put it


                # TODO put in a fct------------------
                ssh = paramiko.SSHClient() 
                host_exist = socket.gethostbyname(hostname)
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                # ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
                ssh.connect(hostname, username=username, password=decrypted_pw)
                command="cd " + path + "; mkdir " + str(exp_objID) #add put file
                # touch filename.json; echo str_file_content >> filename.json
                print("executing ",command)
                stdin , stdout, stderr = ssh.exec_command(command)
                print(stdout.read())
                # sftp = ssh.open_sftp()
                # sftp.put(localpath, path)
                # sftp.close()
                ssh.close()
                # --------------------------

                return render(request, 'repoIndex/endExperiment.html',{'new_exp': new_exp})
            elif valid == "X":
                error_string = "An error occurred in genID validation stage"
                # return render(request, 'repoIndex/errorUploading.html',{'exp_types': exp_types})
                print(error_string)
            else:
                error_string = "Sorry but the following GenIDs are not in the LAS database: \n"
                print(error_string)
                return render(request, 'repoIndex/errorUploading.html',{'error_string': error_string, 'valid': valid})

            # print("description = ",request.POST['description'])
            # lasuser=User.objects.get(username=request.user.username)
            exp_types = db.experiment_types.find({},{"_id":0}).sort("Name",pymongo.ASCENDING)
            # db.experiments.insert( { name: "test_exp", genID: "ZZZ9999XXO0W00000000000000", exp_type: "Test", pipeline: "2", description: "Just some blah blah blah"} )
            # lasuser=User.objects.get(username=request.user.username)
            # wgList=db.social.find({"@type":"WG", "users": {"$in": [request.user.username ]}})
            # ### loginas ###
            # hasPreviousUser = loginas.existsPreviousUser(request)
            # isSuperUser = request.user.is_superuser

        except Exception as e:
            print ('Error AddExperiment', e)
            return redirect('/')

@method_decorator([login_required], name='dispatch')
class QueryExperimentType(View):
    def get(self, request):
        try:
            print("entered QueryExperimentType")
            # lasuser=User.objects.get(username=request.user.username)
            # wgList=db.social.find({"@type":"WG", "users": {"$in": [request.user.username ]}})
            # ### loginas ###
            # hasPreviousUser = loginas.existsPreviousUser(request)
            # isSuperUser = request.user.is_superuser
            return render(request, 'repoIndex/queryExperimentType.html')
        except Exception as e:
            print ('Error QueryExperimentType', e)
            return redirect('/')

@method_decorator([login_required], name='dispatch')
class QueryExperiment(View):
    def post(self, request):
        try:
            print("entered QueryExperiment")
            # print("request is: ",request.POST)

            print("exp_name = ",request.POST['exp_name'])
            print("genID = ",request.POST['genID'])
            print("exp_type = ",request.POST['exp_type'])
            print("pipeline = ",request.POST['pipeline'])
            print("description = ",request.POST['description'])

            exp_name = request.POST['exp_name']
            genID = request.POST['genID']
            exp_type = request.POST['exp_type']
            pipeline = request.POST['pipeline']
            description = request.POST['description']

            query = {}
            if exp_name != "":
                query['exp_name'] = { '$eq': exp_name }
            if genID != "":
                query['genID'] = {'$in': genID} # $in neeed array and genID is not, transform it into
            if exp_type != "":
                query['exp_type'] = { '$eq': exp_type }
            if pipeline != "":
                query['pipeline'] = { '$eq': pipeline }
            # if description != "":
            #     query['description'] = {'/.*description.*/} <---- check this for like query

            print("query is:", query)
            results = db.experiments.find(query)
            for doc in results:
                print(doc)

            exp_types=db.experiment_types.find({},{"_id":0}).sort("Name",pymongo.ASCENDING)

            query_msg = "query results here"
            return render(request, 'repoIndex/endQueryExperiment.html',{'query_msg': query_msg})
        except Exception as e:
            print ('Error QueryExperiment', e)
            return redirect('/')

# @method_decorator([login_required], name='dispatch')
# class ValidateGenID(View):
#     def post(self, request):
#         try:
#             print("Entered validation API")
#             # TODO create separate fcts for validations: hostname, genid, fileformat
#             # received_json_data = json.loads(request.body.decode("utf-8"))
#             print(request)



#             # lasuser=User.objects.get(username=request.user.username)
#             # wgList=db.social.find({"@type":"WG", "users": {"$in": [request.user.username ]}})
#             # ### loginas ###
#             # hasPreviousUser = loginas.existsPreviousUser(request)
#             # isSuperUser = request.user.is_superuser
#             return render(request, 'repoIndex/validateGenID.html')
#         except Exception as e:
#             print ('Error Validation API', e)
#             return redirect('/')