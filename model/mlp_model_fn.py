import tensorflow as tf 

def build_mlp_model(is_training, inputs, params):
    '''Build forward model and compute logits

    Args:
        is_training: (bool) indicates training or evaluation
        inputs: (dict) contains tensors of inputs and labels fed to the graph
        params: (dict) hyperparameters of the model

    Returns:
        output: (tf.tensor) logits of the model
    
    '''
    
    #Read all hyperparameters
    num_fc_layers = params['num_fc_layers']
    fc_hidden_units = params['fc_hidden_units']
    activation = params['activation']
    dropout_rate = params['dropout_rate']
    batch_norm_layer = inputs 
    
    #Construct hidden layers of the forward model
    for layer in range(num_fc_layers):
        with tf.variable_scope('fc_{}'.format(layer+1)):
            hidden_layer = tf.layers.dense(batch_norm_layer, fc_hidden_units[layer], activation)
            dropout_layer = tf.layers.dropout(hidden_layer, rate = dropout_rate,training = is_training)
            batch_norm_layer = tf.layers.batch_normalization(dropout_layer, training = is_training)
        
    #Compute output of the model   
    with tf.variable_scope('output'):
        output = tf.layers.dense(batch_norm_layer, 1, activation)
    
    return output


def mlp_model_fn(is_training, inputs, params):

    '''Define graph operations for training and evaluating
    
    Args:
        is_training: (bool) indicates training or evaluation
        inputs: (dict) contains tensors of inputs and labels fed to the graph
        reuse: (bool) To or not to reuse the variables with same name
        params: (dict) hyperparameters of the model

    Returns:
        model_spec: (dict) Contains the operations needed for training and evaluating the model
    
    '''
    target = inputs['target']
    spectra_data = inputs['spectra_data']

    #Compute logits and make predictions 
    with tf.variable_scope('model', reuse = not is_training):
        logits = build_mlp_model(is_training, spectra_data, **params)
        predictions = tf.cast(tf.greater_equal(tf.sigmoid(logits), params['threshold']), tf.float32)
        
    #Binary cross entropy loss computed across every dimension for multi label classification
    loss = tf.reduce_mean(tf.losses.binary_crossentropy(target, logits, from_logits = True))
    accuracy = tf.reduce_mean(tf.cast(tf.equal(target, predictions), tf.float32))



    if is_training:
        optimizer = tf.train.AdamOptimizer(params['learning_rate'])
        global_step = tf.train.get_or_create_global_step()
        
        #Perform update_op to update moving mean and variance before minimizing the loss
        update_op = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        with tf.control_dependencies(update_op):
            train_op = optimizer.minimize(loss, global_step = global_step)
    
    
    with tf.variable_scope('metrics'):
        metrics = {'loss' : tf.metrics.mean(loss),
                   'accuracy' : tf.metrics.accuracy(target, predictions)}
        
    
        
    #Group all metrics update ops 
    metrics_update_op = tf.group(*[metric[1] for _, metric in metrics.items()])
        
    #Collect all metrics variables to initialize before every epoch
    metrics_variables = tf.get_collection(tf.GraphKeys.LOCAL_VARIABLES, scope="metrics")
    metrics_initializer_op = tf.variables_initializer(metrics_variables)
        
    tf.summary.scalar('loss', loss)
    tf.summary.scalar('accuracy', accuracy)
        
    model_spec = inputs
    model_spec['loss'] = loss
    model_spec['predictions'] = predictions
    model_spec['metrics'] = metrics
    model_spec['metric_initializer_op'] = metrics_initializer_op
    model_spec['metrics_update_op'] = metrics_update_op
    model_spec['summary_op'] = tf.summary.merge_all()
    model_spec['variables_init_op'] = tf.global_variables_initializer()
    
    
    if is_training:
        model_spec['train_op'] = train_op
    
    return model_spec