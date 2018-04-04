import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';
import socketIOClient from 'socket.io-client'
import { Button , ButtonGroup, Alert, Input} from 'reactstrap';

class App extends Component {
    constructor(props){
        super(props);
        this.state = {
            runMode: 0,
            status: -1,
            log: '',
            endpoint: 'http://192.168.3.1/',
            cmdStr: '',
            response: '',
            cmdResponse: '',
            aligned : false,
            engaged : false,
            disableReset: false
        };
        const {endpoint} = this.state;
        console.log(this.state.response);
        this.socket = socketIOClient(endpoint);
        this.onModeSelectClick = this.onModeSelectClick.bind(this);
        this.onStepClick = this.onStepClick.bind(this);
        this.onResetClick = this.onResetClick.bind(this);
    }

    onModeSelectClick(num) {
        var self = this;
        self.socket.emit('mode', num);
    }

    onStepClick(){
        var self = this;
        self.socket.emit('step', ()=>{
            console.log("step");
        });
    }

    onResetClick(){
        var self = this;
        self.socket.emit('reset', ()=>{
            console.log('Reset triggered!');
        });
    }

    getColor(){
        switch(this.state.status){
            case 0:
                return "success";

            case 1:
                return "warning";

            case 2:
                return "danger";

            case 3:
                return "primary";

            default:
                return "secondary";
        }
    }

    getStatusText(){
        switch(this.state.status){
            case 0:
                return "Success!";

            case 1:
                return "Running...";

            case 2:
                return "ERROR!!!";

            case 3:
                return "Charge Engaged!"

            default:
                return "Ready!";
        }
    }

    componentDidMount() {
        var self = this;
        // Got connection to server
        self.socket.on("connect", (data) => {
            console.log('Connected to server!');
            this.setState(data);    // Synchronize state
        });

        self.socket.on("state", (state) => {
            console.log('State update!');
            console.log(state);
            this.setState(state);
        });
    }

     render() {
         const { response } = this.state;
         const { cmdStr } = this.state;
         return (
              <div className="App">
                <header className="App-header">
                <img src={logo} className="App-logo" alt="logo" />
                <h1 className="App-title">Automatic Vehicle Charger Controls</h1>
                </header>
                <div> </div>
                <div className="Container">
                <div className="ImgBox">
                    <img src="/video_feed" alt="Current detection feed"/>
                </div>
                <div className="Seperator">
                </div>
                <div className="ControlPane">
                <Alert color={this.getColor()}>
                    {this.getStatusText()}
                </Alert>

                <div>
                    Current Command:
                </div>

                <Input type="textarea" rows="1" value={cmdStr} disabled>

                </Input>

                <div id="ModeSelect">
                    <div>
                    Mode Select:
                    </div>

                    <ButtonGroup>
                        <Button onClick={()=>this.onModeSelectClick(0)} active={this.state.runMode===0} disabled={!(this.state.status===-1) && !(this.state.runMode===0)}>
                            Auto
                        </Button>
                        <Button onClick={()=>this.onModeSelectClick(1)} active={this.state.runMode===1} disabled={!(this.state.status===-1) && !(this.state.runMode===1)}>
                            Step
                        </Button>
                    </ButtonGroup>
                </div>

                <div id="ButtonStart">
                    <Button onClick={() => this.onStepClick()} block disabled={(this.state.status===1) || (this.state.status===3)}>
                        {this.state.runMode===0 ? "Start" : "Step"}
                    </Button>
                </div>

                <div id="ButtonReset">
                    <Button onClick={() => this.onResetClick()} block disabled={this.state.disableReset}>
                        Reset
                    </Button>
                </div>

            </div>
        </div>

        <div className="footer">
            <p align="left">
                Live log:
            </p>
            <Input id="liveLog" type="textarea" rows="4" value={response} disabled>
            </Input>
        </div>
    </div>
    );
    }
}

export default App;
