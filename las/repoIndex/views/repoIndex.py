from .__init__ import *
from .hostManager import *
from jsonschema import validate
from bson.json_util import dumps
from django.http import JsonResponse
from bson.objectid import ObjectId
import pymongo
import requests
import os
import paramiko
import bcrypt
import fileinput
import jsonschema
import simplejson as json

# TODO DELETE LATER (inspection line)
# from ...LASUtils.mongodb import db

key = b'n_jrI9S9ivI9iYQDEfVPqfntsxFyfSBp8375JFvIsxM='

# genID_schema = {
#     "type" : "object",
#     "properties" : {
#         "genID" : {"type" : "array"},
#     },
#     "required": ["genID"]
# }

# descr_schema = {
#     "type" : "object",
#     "properties" : {
#         "description" : {"type" : "string"},
#     },
#     "required": ["description"]
# }

@method_decorator([login_required], name='dispatch')
class LandAddExperiment(View):
    def get(self, request):
        return render(request, 'repoIndex/addExperiment.html')

@method_decorator([login_required], name='dispatch')
class LandQueryExperimentType(View):
    def get(self, request):
        try:
            print("REQUEST IS:", request.GET)
            if request.GET.get("q"):
                print("received query")
                param = str(request.GET.get("q"))
                print ("param is:", param)
                exp_types = db.experiment_types.find({ "Name": {'$regex' : ".*"+param+".*", '$options': "ix"} },{"_id":0}).sort("Name",pymongo.ASCENDING)
                # doc = db[dbcollection].find({fieldFilter:{"$regex":regex, "$options": 'ix'}, 'access_w': {'$exists': True, '$in': user['heritage']['w']} }).limit(10)
                print('exp_types is:', exp_types)
                return JsonResponse(to_json(exp_types), safe=False)
            else:
                exp_types = db.experiment_types.find({},{"_id":0}).sort("Name",pymongo.ASCENDING)
                print('exp_types is:',exp_types)
                return render(request, 'repoIndex/queryExperimentType.html',{'exp_types': exp_types})
        except Exception as e:
            print ('Error LandQueryExperimentType', e)
            error_string = "Error retrieving experiment types " + str(e)
            return render(request,'repoIndex/errorQuery.html',{'error_string': error_string})

@method_decorator([login_required], name='dispatch')
class LandQueryExperiment(View):
    def get(self, request):
        return render(request, 'repoIndex/queryExperiment.html')

@method_decorator([login_required], name='dispatch')
class LandNewExperimentType(View):
    def get(self, request):
        return render(request, 'repoIndex/newExperimentType.html')

@method_decorator([login_required], name='dispatch')
class LandValidateGenID(View):
    def get(self, request):
        return render(request, 'repoIndex/validateGenID.html')

def validateJSONschema_old(json_file,schema):
    try:
        data = json.loads(json_file)
        print(data)
        # print("Schema is:", schema)
        validate(instance=data, schema=schema)
        print("JSON valid")
        return (data)
    except Exception as e:
        err_msg = "Error in validating JSON schema: " + str(e)
        # print(err_msg)
        return (err_msg)

def validateJSONschema(data):
    try:
        print("entered validateJSONschema")
        cwd = os.getcwd()
        print(cwd)
        with open('genomic_metadata.schema.json', 'r') as f:
            schema_data = f.read()
            schema = json.loads(schema_data)
    except Exception as e:
        err_msg = "Error in JSON schema file: " + str(e)
        print(err_msg)
        return (err_msg)
    try:
        validation = jsonschema.validate(data, schema)
        print("JSON valid")
        return (data)
    except Exception as e:
        err_msg = "Error in validating against JSON schema: " + str(e)
        print(err_msg)
        return (err_msg)

def extract_GenID(key, var):
    print("entered extract_GenID")
    arr = []
    for j in var:
        if hasattr(j,'items'):
            # print("j is:",j)
            for k, v in j.items():
                if j[key] == True:
                    if k == key:
                        print("found",key,"= True for",j['id'])
                        arr.append(j['id'])
    return arr

# def wrapvalidateJSONschema(json_file,schema,request):
#     try:
#         schema_valid = validateJSONschema(json_file,schema)
#         if schema_valid != "OK":
#             print(schema_valid)
#             return RedirectIfWrong(request,'repoIndex/errorUploading.html',{'error_string': str(schema_valid)})
#         return "OK"
#     except Exception as e:
#         err_msg = "Error in JSON schema validation function"
#         print(err_msg)
#         return RedirectIfWrong(request,'repoIndex/errorUploading.html',{'error_string': str(err_msg)})

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

def makeexperimentfolder(hostname,username,password,path,exp_id):
    try:
        ssh = paramiko.SSHClient() 
        host_exist = socket.gethostbyname(hostname)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password)
        command="cd " + path + "; mkdir " + str(exp_id)
        # touch filename.json; echo str_file_content >> filename.json
        print("executing ",command)
        stdin , stdout, stderr = ssh.exec_command(command)
        print(stdout.read())
        # sftp = ssh.open_sftp()
        # sftp.put(localpath, path)
        # sftp.close()
        ssh.close()
        return ("OK")
    except paramiko.ssh_exception.NoValidConnectionsError as error:
        # print("Failed to connect to host '%s' with error: %s" % (hostname, error))
        error_msg = "Failed to connect to host " + hostname + " with error " + str(error)
        print(error_msg)
        ssh.close()
        return (error_msg)
    except paramiko.AuthenticationException as authexp:
        error_msg = "Authentication failed for user " + username + "@" + hostname + " with provided password.\n Please verify your credentials"
        print(error_msg)
        ssh.close()
        return (error_msg)
    except paramiko.SSHException as sshException:
        print("Could not establish SSH connection: ", sshException)
        error_msg = "Could not establish SSH connection"
        print(sshException)
        ssh.close()
        return (error_msg)
    except socket.timeout as e:
        print("Connection timed out")
        error_msg = "Connection timed out"
        print(e)
        ssh.close()
        return (error_msg)
    except socket.error as e:
        print("socket Error")
        error_msg = "Failed to resolve hostname " + hostname +" \n"+str(e)
        ssh.close()
        return (error_msg)
    except Exception as e:
        error_msg = "Error occurred during connection test: " + str(e)
        print(error_msg)
        ssh.close()
        return (error_msg)

@method_decorator([login_required], name='dispatch')
class AddExperiment(View):
    def post(self, request):
        try:
            print("entered AddExperiment")
            # print("request is: ",request.POST)
            print("request genID file is: ",request.FILES['exp_file'])

            hostname = request.POST['hostname']
            # exp_name = request.POST['exp_name']
            # exp_type = request.POST['exp_type']
            exp_host_username = request.POST['exp_host_username']

            wb_expFile = request.FILES['exp_file'].read()
            wb = wb_expFile.decode("utf-8")
            data_exp = json.loads(wb)
            print("data_exp is:")
            print(data_exp)
            # print("wb")
            # print(wb)
            # data_expFile = json.loads(wb_expFile)
            # print(data_expFile)
            data_expFile = validateJSONschema(data_exp)
            if "file" in data_expFile:
                print(data_expFile)
                return render(request,'repoIndex/errorUploading.html',{'error_string': data_expFile})
            elif "validating" in data_expFile:
                print(data_expFile)
                return render(request,'repoIndex/errorUploading.html',{'error_string': data_expFile})

            print("schema_valid of experiment file = OK")
            print("About to extract genIDs from json file")
            genid_list = list(extract_GenID("LAS_Validation",data_exp['samples_map']))
            print("GENIDS are:")
            print(genid_list)
            if len(genid_list) > 0:
                valid = validateGenID(genid_list)
            else:
                print("All GenIDs did not require validation")
                valid = "OK"

            print("valid is:", valid)

            if valid == "OK":
                exp_name = data_exp['name']
                print("exp_name is:", exp_name)
                existing_exp = db.experiments.find_one({'name': exp_name})
                print("existing_exp is:",existing_exp)

                exp_type = data_exp['technology']['library']['type']
                existing_type = db.experiment_types.find_one({'Name': exp_type})
                print("exp_type is:", existing_type)

                if existing_exp is not None:
                    error_string = "The chosen Experiment Name (" + exp_name + ") already exists"
                    print(error_string)
                    return render(request, 'repoIndex/errorUploading.html',{'error_string': error_string})
                elif existing_type is None:
                    error_string = "The chosen Experiment Type (" + exp_type + ") does not exist"
                    print(error_string)
                    return render(request, 'repoIndex/errorUploading.html',{'error_string': error_string})
                else:
                    new_exp = db.experiments.insert_one(data_exp)
                # if valid == "OK":
                #     new_exp = db.experiments.update_one(
                #         { 'exp_name': exp_name },
                #         {"$setOnInsert":{
                #             'exp_name': exp_name,
                #             'genID': data_expFile['genID'],
                #             'exp_type': exp_type,
                #             'pipeline': pipeline,
                #             'description': data_descr['description']
                #             }
                #         },
                #         upsert = True
                #         )
                    
                    exp_objID = new_exp.inserted_id
                    print("new_exp _id is:", exp_objID)

                    doc = db.hosts.find_one({'hostname' : hostname, 'host_username' : exp_host_username}, {'description' :0, '_id': 0})
                    print("doc is: ",doc)
                    username = doc['host_username']
                    password = doc['host_password']
                    path = doc['host_path']
                    # print("inserted_host is:", inserted_host['host_path'])

                    # TODO put Fernet encr and decr in separate fcts decrypted_pw=fct(key,password)
                    print("K:",key)
                    f = Fernet(key)
                    print("F:",f)
                    encrypted_pw = password
                    decrypted_pw = f.decrypt(encrypted_pw)
                    print("ENC",encrypted_pw)

                    # print(username['host_username'])
                    # print(password['host_password'])
                    # print(path['host_path'])
                    # decrypted_pw = decr(key,password)
                    conn_test = testConnection(hostname,username,decrypted_pw,path)
                    print("conn_test is: ", conn_test)
                    if conn_test != "OK":
                        print(conn_test)
                        return render(request, 'repoIndex/errorUploading.html',{'error_string': conn_test})

                    make_folder = makeexperimentfolder(hostname,username,decrypted_pw,path,exp_objID)
                    print("make_folder is: ", make_folder)
                    if make_folder != "OK":
                        print(conn_test)
                        return render(request, 'repoIndex/errorUploading.html',{'error_string': make_folder})
                
                    if path.endswith("/"):
                        path = path[:-1]

                    exp_path = username+"@"+hostname+path+"/"+str(exp_objID)
                    print("exp_path is:", exp_path)
                    db.experiments.update({'_id': exp_objID}, {"$set": {'path': exp_path}})
                    
                    inserted_exp = db.experiments.find_one({"_id" : exp_objID })
                    print("inserted_exp is:", inserted_exp)

                    return render(request, 'repoIndex/endExperiment.html',{'inserted_exp': inserted_exp})
            elif valid == "X":
                error_string = "An error occurred in GenID validation stage"
                print(error_string)
                return render(request, 'repoIndex/errorUploading.html',{'error_string': error_string})
            else:
                error_string = "Sorry but the following GenIDs are not in the LAS database: \n"
                print(error_string)
                return render(request, 'repoIndex/errorUploading.html',{'error_string': error_string, 'valid': valid})

        except Exception as e:
            print ("Error AddExperiment", e)
            error_string = "Error adding experiment " + str(e)
            return render(request,'repoIndex/errorUploading.html',{'error_string': error_string})

@method_decorator([login_required], name='dispatch')
class QueryExperimentType(View):
    def get(self, request):
        try:
            print("entered QueryExperimentType")
            return render(request, 'repoIndex/queryExperimentType.html')
        except Exception as e:
            print ('Error QueryExperimentType', e)
            error_string = "Error querying experiment type " + str(e)
            return render(request, 'repoIndex/errorQuery.html',{'error_string': error_string})

@method_decorator([login_required], name='dispatch')
class NewExperimentType(View):
    def post(self, request):
        try:
            print("entered NewExperimentType")

            print("exp_type_name = ",request.POST['exp_type_name'])
            print("exp_type_description = ",request.POST['exp_type_description'])

            exp_type_name = request.POST['exp_type_name']
            exp_type_description = request.POST['exp_type_description']

            existing_types = db.experiment_types.find_one({'Name' : exp_type_name},{"_id":0})

            if existing_types:
                existing_name = existing_types['Name']
                existing_desc = existing_types['Description']
                print("exist name", existing_name)
                print("exist desc", existing_desc)
                error_string = "Sorry but type \""+exp_type_name+"\" already exists. \n Name: "+existing_name+"\n Description: "+existing_desc
                print(error_string)
                return render(request, 'repoIndex/errorNewExperimentType.html',{'error_string': error_string})
            
            new_exp_type = db.experiment_types.update_one(
                    { 'Name': exp_type_name },
                    {"$setOnInsert":{
                        'Name': exp_type_name,
                        'Description': exp_type_description,
                        }
                    },
                    upsert = True
                    )
                
            inserted_type = db.experiment_types.find_one({'name' : exp_type_name})
            print("inserted_type is:", inserted_type)

            return render(request, 'repoIndex/endNewExperimentType.html',{'inserted_type': inserted_type})

        except Exception as e:
            print ("Error NewExperimentType", e)
            error_string = "Error inserting new experiment type " + str(e)
            return render(request, 'repoIndex/errorNewExperimentType.html',{'error_string': error_string})

@method_decorator([login_required], name='dispatch')
class QueryExperiment(View):
    def post(self, request):
        try:
            print("entered QueryExperiment")
            # print("request is: ",request.POST)

            print("exp_name = ",request.POST['exp_name'])
            print("genID = ",request.POST['genID'])
            print("exp_type = ",request.POST['exp_type'])
            print("exp_source_vendor = ",request.POST['exp_source_vendor'])
            print("exp_seqplat_vendor = ",request.POST['exp_seqplat_vendor'])
            print("path = ",request.POST['path'])
            # print("description = ",request.POST['description'])

            exp_name = request.POST['exp_name']
            exp_genID = request.POST['genID']
            exp_type = request.POST['exp_type']
            exp_source_vendor = request.POST['exp_source_vendor']
            exp_seqplat_vendor = request.POST['exp_seqplat_vendor']
            exp_path = request.POST['path']

            # if exp_genID != "":
            #     genID = exp_genID.split("\r\n")
            #     print("genId is:",genID)
            #     print("len genid:", len(genID))
            # else:
            #     genID = ""

            query = {}
            if exp_name != "":
                # query['exp_name'] = { '$eq': exp_name }
                query['name'] = { '$regex' : ".*"+exp_name+".*", '$options': "i"}
            if exp_genID != "":
                query['samples_map.id'] = { '$regex' : ".*"+exp_genID+".*", '$options': "ix"}
            if exp_type != "":
                # query['exp_type'] = { '$eq': exp_type }
                query['technology.library.type'] = { '$regex' : ".*"+exp_type+".*", '$options': "i"}
            if exp_source_vendor != "":
                query['source.vendor'] = { '$regex' : ".*"+exp_source_vendor+".*", '$options': "i"}
            if exp_seqplat_vendor != "":
                query['technology.sequencing_platform.vendor'] = { '$regex' : ".*"+exp_seqplat_vendor+".*", '$options': "i"}
            if exp_path != "":
                query['path'] = { '$regex' : ".*"+exp_path+".*", '$options': "ix"}
            # if order_date != "":
            #     # query['pipeline'] = { '$eq': pipeline }
            #     query['pipeline'] = {date interval}
            # if received_date != "":
            #     query['description'] = {date interval}

            #add filters by user

            print("query is:", query)
            results = list(db.experiments.find(query,{"_id":0}).sort("exp_name",pymongo.ASCENDING))
            for doc in results:
                print(doc)
            
            # print("results is: ", results)
            # gen_id_list = list(db.experiments.find(query,{"_id":0}).sort("exp_name",pymongo.ASCENDING))
            # exp_types=db.experiment_types.find({},{"_id":0}).sort("Name",pymongo.ASCENDING)
            # print('exp_types is:',exp_types)
            # return render(request, 'repoIndex/queryExperimentType.html',{'exp_types': exp_types})

            return render(request, 'repoIndex/endQueryExperiment.html',{'results': results})
        except Exception as e:
            print ("Error QueryExperiment", e)
            error_string = "Error executing your query " + str(e)
            return render(request,'repoIndex/errorQuery.html',{'error_string': error_string})

